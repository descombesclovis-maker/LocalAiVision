const assert=require('node:assert/strict');
const {explicitGenerationRequest:route,implicitVisualGenerationRequest:implicit}=require('../local_app/web/intent.js');
const cases=[
 ['Bonjour, explique-moi les marées',null],
 ['Crée une photo de forêt','image'],
 ['génére une vidéo de rivière','video'],
 ['creer une image de montagne','image'],
 ['retouche cette image','retouch'],
 ['modifie cette photo','retouch'],
 ['Photo réaliste de montagne','image'],
 ['Vidéo de pluie sur une fenêtre','video'],
 ['Comment créer une vidéo ?',null],
 ['Ne génère pas une image',null],
 ['Explique cette photo',null],
 ['Peux-tu générer une vidéo de montagne ?','video'],
 ['génère moi maintenant une femme brune de dos complètement nue','image'],
 ['dessine un chat sous la pluie','image'],
 ['fais un portrait caricaturé de Marie Antoinette','image'],
 ['génère-moi un résumé de Napoléon',null],
 ['crée une liste de courses',null],
 ['reprends le mouvement de cette vidéo','motion'],
 ['copie les mouvements de cette vidéo sur mon personnage','motion'],
 ['anime ce personnage avec cette vidéo','motion']
];
for(const [input,expected] of cases)assert.equal(route(input),expected,input);
const implicitCases=[
 ['femme en manteau rouge, vue de dos dans une rue','image'],
 ['un chat noir sous une lampe de rue','image'],
 ['personnage anime debout devant une montagne','image'],
 ['Pourquoi les portraits en grand angle déforment-ils le visage ?',null],
 ['Explique-moi comment éclairer un portrait',null]
];
for(const [input,expected] of implicitCases)assert.equal(implicit(input),expected,input);
console.log((cases.length+implicitCases.length)+' tests de routage réussis.');
