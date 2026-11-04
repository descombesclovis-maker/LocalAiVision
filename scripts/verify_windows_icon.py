"""Check the compiled EXE's real Windows icons against the entire approved logo.

Runs on the isolated Windows CI desktop; never touches a user's shortcuts/data.
Uses Shell/Win32 extraction, an ephemeral shortcut and the real native window.
"""
from __future__ import annotations
import argparse
import ctypes
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

from PIL import Image, ImageChops, ImageGrab, ImageStat


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('executable', type=Path)
    parser.add_argument('--output', type=Path, default=Path('build/icon-qa'))
    args = parser.parse_args()
    if os.name != 'nt':
        raise RuntimeError('Windows Shell icon verification requires Windows.')
    exe, output = args.executable.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    with Image.open(root/'local_app/web/assets/brand-reference/LocalAIStudio_Official_Original.png') as source:
        master = source.convert('RGBA')
    user, shell, gdi, kernel = ctypes.windll.user32, ctypes.windll.shell32, ctypes.windll.gdi32, ctypes.windll.kernel32

    class BITMAP(ctypes.Structure):
        _fields_ = [('type',W.LONG),('width',W.LONG),('height',W.LONG),('row',W.LONG),('planes',W.WORD),('bits_per_pixel',W.WORD),('bits',ctypes.c_void_p)]
    class ICONINFO(ctypes.Structure):
        _fields_ = [('icon',W.BOOL),('x',W.DWORD),('y',W.DWORD),('mask',W.HBITMAP),('color',W.HBITMAP)]
    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [('size',W.DWORD),('width',W.LONG),('height',W.LONG),('planes',W.WORD),('bits',W.WORD),('compression',W.DWORD),('image_size',W.DWORD),('x',W.LONG),('y',W.LONG),('used',W.DWORD),('important',W.DWORD)]
    class BITMAPINFO(ctypes.Structure):
        _fields_ = [('header',BITMAPINFOHEADER),('colors',W.DWORD * 3)]
    class SHFILEINFO(ctypes.Structure):
        _fields_ = [('icon',W.HICON),('index',ctypes.c_int),('attrs',W.DWORD),('display',W.WCHAR * 260),('type',W.WCHAR * 80)]

    user.GetIconInfo.argtypes = [W.HICON,ctypes.POINTER(ICONINFO)]
    user.GetDC.argtypes=[W.HWND];user.GetDC.restype=W.HDC
    user.ReleaseDC.argtypes=[W.HWND,W.HDC]
    user.DrawIconEx.argtypes=[W.HDC,ctypes.c_int,ctypes.c_int,W.HICON,ctypes.c_int,ctypes.c_int,W.UINT,W.HBRUSH,W.UINT]
    user.DestroyIcon.argtypes=[W.HICON]
    user.SendMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM];user.SendMessageW.restype=ctypes.c_void_p
    user.GetClassLongPtrW.argtypes=[W.HWND,ctypes.c_int];user.GetClassLongPtrW.restype=ctypes.c_void_p
    gdi.GetObjectW.argtypes=[W.HANDLE,ctypes.c_int,ctypes.c_void_p]
    gdi.CreateCompatibleDC.argtypes=[W.HDC];gdi.CreateCompatibleDC.restype=W.HDC
    gdi.CreateDIBSection.argtypes=[W.HDC,ctypes.POINTER(BITMAPINFO),W.UINT,ctypes.POINTER(ctypes.c_void_p),W.HANDLE,W.DWORD];gdi.CreateDIBSection.restype=W.HBITMAP
    gdi.SelectObject.argtypes=[W.HDC,W.HANDLE];gdi.SelectObject.restype=W.HANDLE
    gdi.DeleteObject.argtypes=[W.HANDLE];gdi.DeleteDC.argtypes=[W.HDC]
    shell.ExtractIconExW.argtypes=[W.LPCWSTR,ctypes.c_int,ctypes.POINTER(W.HICON),ctypes.POINTER(W.HICON),W.UINT]
    shell.SHGetFileInfoW.argtypes=[W.LPCWSTR,W.DWORD,ctypes.POINTER(SHFILEINFO),W.UINT,W.UINT];shell.SHGetFileInfoW.restype=ctypes.c_size_t

    results={'executable':exe.name,'checks':{},'limits':['Windows may retain an already-pinned icon in its user-specific icon cache. No user cache was cleared.']}
    def image_for(handle):
        info=ICONINFO()
        if not user.GetIconInfo(handle,ctypes.byref(info)):
            raise RuntimeError('GetIconInfo failed.')
        bitmap=BITMAP()
        try:
            if not gdi.GetObjectW(info.color,ctypes.sizeof(bitmap),ctypes.byref(bitmap)):
                raise RuntimeError('Icon color bitmap unavailable.')
            width,height=bitmap.width,bitmap.height
        finally:
            if info.color:gdi.DeleteObject(info.color)
            if info.mask:gdi.DeleteObject(info.mask)
        screen=user.GetDC(None);dc=gdi.CreateCompatibleDC(screen)
        fmt=BITMAPINFO();fmt.header.size=ctypes.sizeof(BITMAPINFOHEADER)
        fmt.header.width=width;fmt.header.height=-height;fmt.header.planes=1;fmt.header.bits=32
        pixels=ctypes.c_void_p();dib=gdi.CreateDIBSection(screen,ctypes.byref(fmt),0,ctypes.byref(pixels),None,0)
        if not dib:raise RuntimeError('CreateDIBSection failed.')
        previous=gdi.SelectObject(dc,dib)
        try:
            ctypes.memset(pixels,0,width*height*4)
            if not user.DrawIconEx(dc,0,0,handle,width,height,0,None,3):raise RuntimeError('DrawIconEx failed.')
            return Image.frombytes('RGBA',(width,height),ctypes.string_at(pixels,width*height*4),'raw','BGRA')
        finally:
            gdi.SelectObject(dc,previous);gdi.DeleteObject(dib);gdi.DeleteDC(dc);user.ReleaseDC(None,screen)

    def verify(handle,label):
        if not handle:raise RuntimeError(label+': Windows did not return an icon.')
        actual=image_for(handle)
        expected=master.resize(actual.size,Image.Resampling.LANCZOS)
        difference=ImageChops.difference(actual.convert('RGB'),expected.convert('RGB'))
        error=max(ImageStat.Stat(difference).mean)
        actual.save(output/(label+'.png'))
        results['checks'][label]={'size':list(actual.size),'mean_rgb_error':error,'passed':error < 0.1}
        if error >= 0.1:raise AssertionError(label+': icon differs from the complete approved logo (mean error '+str(error)+').')

    large,small=W.HICON(),W.HICON()
    extracted = shell.ExtractIconExW(str(exe),0,ctypes.byref(large),ctypes.byref(small),1)
    # With both output arrays Windows can return two extracted handles.
    if extracted == 0 or not large or not small:
        raise RuntimeError('The EXE has no extractable icon resource.')
    try:
        verify(large,'exe-large');verify(small,'exe-small')
    finally:
        user.DestroyIcon(large);user.DestroyIcon(small)
    info=SHFILEINFO()
    if not shell.SHGetFileInfoW(str(exe),0,ctypes.byref(info),ctypes.sizeof(info),0x100):
        raise RuntimeError('Windows Shell could not extract the Explorer icon.')
    try:verify(info.icon,'explorer-shell')
    finally:user.DestroyIcon(info.icon)

    # This is the same executable resource reference used by the updater's
    # shortcuts (IconLocation = "$CurrentExe,0"). No real shortcut is changed.
    with tempfile.TemporaryDirectory(prefix='localai-icon-qa-', ignore_cleanup_errors=True) as tmp:
        link=Path(tmp)/'LocalAiStudio-test.lnk'
        script="$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:ICON_QA_LINK);$s.TargetPath=$env:ICON_QA_EXE;$s.IconLocation=$env:ICON_QA_EXE+',0';$s.Save();$r=(New-Object -ComObject WScript.Shell).CreateShortcut($env:ICON_QA_LINK);if($r.TargetPath -ne $env:ICON_QA_EXE -or $r.IconLocation -ne ($env:ICON_QA_EXE+',0')){throw 'Shortcut icon reference mismatch'}"
        subprocess.run(['powershell','-NoProfile','-Command',script],env={**os.environ,'ICON_QA_LINK':str(link),'ICON_QA_EXE':str(exe)},check=True)
        results['checks']['shortcut']={'passed':link.is_file(),'icon_location':exe.name+',0'}
        if not link.is_file():raise RuntimeError('Shortcut was not created.')

        # Find the actual GUI process, including the onefile bootloader child.
        kernel.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];kernel.OpenProcess.restype=W.HANDLE
        kernel.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,ctypes.POINTER(W.DWORD)]
        kernel.CloseHandle.argtypes=[W.HANDLE]
        user.GetWindowThreadProcessId.argtypes=[W.HWND,ctypes.POINTER(W.DWORD)]
        user.GetWindowTextW.argtypes=[W.HWND,W.LPWSTR,ctypes.c_int]
        user.IsWindowVisible.argtypes=[W.HWND]
        callback_type=ctypes.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
        user.EnumWindows.argtypes=[callback_type,W.LPARAM]
        found=[]
        def inspect(hwnd,_):
            if not user.IsWindowVisible(hwnd):return True
            title=ctypes.create_unicode_buffer(1024);user.GetWindowTextW(hwnd,title,1024)
            if not title.value.startswith('LocalAI Studio'):return True
            pid=W.DWORD();user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
            process=kernel.OpenProcess(0x1000,False,pid.value)
            if process:
                try:
                    buf=ctypes.create_unicode_buffer(32768);size=W.DWORD(len(buf))
                    if kernel.QueryFullProcessImageNameW(process,0,buf,ctypes.byref(size)) and Path(buf.value).resolve()==exe:
                        found.append(hwnd)
                finally:kernel.CloseHandle(process)
            return True
        callback=callback_type(inspect)
        env={**os.environ,'LOCALVISIONAI_DATA':str(Path(tmp)/'data'),'LOCALVISIONAI_SKIP_SETUP':'1','LOCALVISIONAI_DISABLE_AUTO_UPDATE':'1'}
        env.pop('LOCALVISIONAI_UPDATE_SMOKE',None)
        proc=subprocess.Popen([str(exe)],env=env)
        try:
            deadline=time.monotonic()+90
            while time.monotonic()<deadline and not found:
                user.EnumWindows(callback,0)
                if not found:time.sleep(0.3)
            if not found:raise RuntimeError('Native Studio window was not observed on this Windows runner.')
            hwnd=found[0]
            icon=user.SendMessageW(hwnd,0x7F,1,0) or user.GetClassLongPtrW(hwnd,-14)
            verify(icon,'native-window-taskbar')
            # A visible native frame can precede WebView2's first paint. Wait
            # for actual non-blank client pixels before calling this a UI proof.
            user.ShowWindow.argtypes=[W.HWND,ctypes.c_int]
            user.GetClientRect.argtypes=[W.HWND,ctypes.POINTER(W.RECT)]
            user.ClientToScreen.argtypes=[W.HWND,ctypes.POINTER(W.POINT)]
            user.SetForegroundWindow.argtypes=[W.HWND]
            user.ShowWindow(hwnd,3)
            user.SetForegroundWindow(hwnd)
            painted=False
            deadline=time.monotonic()+60
            while time.monotonic()<deadline:
                rect=W.RECT();origin=W.POINT(0,0)
                user.GetClientRect(hwnd,ctypes.byref(rect));user.ClientToScreen(hwnd,ctypes.byref(origin))
                capture=ImageGrab.grab(bbox=(origin.x,origin.y,origin.x+rect.right,origin.y+rect.bottom))
                luma=capture.convert('L')
                stats=ImageStat.Stat(luma)
                visible_fraction=sum(luma.histogram()[40:])/max(1,capture.width*capture.height)
                # The window background is near-black (#090909); its fill and
                # anti-aliased edges must not count as a successfully painted UI.
                if stats.mean[0]>2 and stats.stddev[0]>8 and visible_fraction>=0.02:
                    painted=True;capture.save(output/'native-window-content.png');break
                time.sleep(.5)
            if not painted:
                capture.save(output/'native-window-blank.png')
                raise RuntimeError('The native window icon is correct, but its WebView content stayed blank.')
            results['checks']['native-content-painted']={'passed':True,'luma_mean':stats.mean[0],'luma_stddev':stats.stddev[0],'visible_fraction_over_40':visible_fraction}
            ImageGrab.grab(all_screens=True).save(output/'windows-desktop.png')
            results['checks']['native-desktop-capture']={'passed':True}
        finally:
            subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
            startup_log=Path(env['LOCALVISIONAI_DATA'])/'logs'/'startup.log'
            if startup_log.is_file():
                (output/'native-startup.log').write_text(startup_log.read_text(encoding='utf-8',errors='replace'),encoding='utf-8')
    (output/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(json.dumps(results,indent=2))


if __name__ == '__main__':
    main()
