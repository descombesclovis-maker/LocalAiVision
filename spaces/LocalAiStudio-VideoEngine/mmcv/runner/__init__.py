import torch.distributed as dist


def get_dist_info():
    if dist.is_available() and dist.is_initialized():
        return dist.get_rank(), dist.get_world_size()
    return 0, 1


__all__ = ["get_dist_info"]
