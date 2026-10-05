/* Pure routing helper, shared by the interface and regression tests. */
function explicitGenerationRequest(text) {
 const t=text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
 if (/\b(ne\s+(?:\w+\s+){0,2}(?:genere|cree|fais).*\bpas|explique|comment|pourquoi|qu['’]est|peux.tu expliquer)\b/.test(t)) return null;
 const action=/\b(cree|creer|genere|generer|produis|produire|fais|faire|fabrique|fabriquer|dessine|dessiner|illustre|illustrer|anime|animer|retouche|retoucher|modifie|modifier|corrige|corriger|transforme|transformer)\b/.test(t);
 const video=/\b(videos?|animations?|films?|clips?)\b/.test(t);
 const image=/\b(photos?|images?|portraits?|illustrations?|visuels?|dessins?|caricatures?|affiches?|logos?)\b/.test(t);
 const retouch=/\b(retouche|retoucher|modifie|modifier|corrige|corriger)\b/.test(t);
 const motion=/\b(transfert\s+de\s+mouvement|motion\s*transfer|reprends?\s+(?:le|les)\s+mouvements?|copie\s+(?:le|les)\s+mouvements?|a\s+partir\s+de\s+cette\s+video|anime\s+.*\s+avec\s+.*\s+video)\b/.test(t);
 const textOutput=/\b(textes?|reponses?|resumes?|syntheses?|poemes?|histoires?|articles?|lettres?|mails?|emails?|messages?|listes?|plans?|codes?|scripts?|programmes?|tableaux?|explications?|recettes?)\b/.test(t);
 const visualSubject=/\b(femmes?|hommes?|filles? adultes?|garcons? adultes?|personnes?|personnages?|visages?|corps|silhouettes?|modeles?|mannequins?|animaux?|chats?|chiens?|voitures?|maisons?|batiments?|paysages?|forets?|montagnes?|plages?|villes?|rues?|scenes?|decors?|objets?|produits?)\b/.test(t);
 const drawingAction=/\b(dessine|dessiner|illustre|illustrer)\b/.test(t);
 if (action && retouch) return 'retouch';
 if (motion) return 'motion';
 if (action && (video || /\b(anime|animer)\b/.test(t))) return 'video';
 if (action && image) return 'image';
 // Natural visual prompts often omit the word "photo" or "image" entirely
 // (e.g. "génère-moi une femme brune de dos"). Route those directly to
 // the image engine instead of letting the text model answer the request.
 if (action && !textOutput && (visualSubject || drawingAction)) return 'image';
 if (/^(une?\s+)?(photo|image|portrait|illustration|dessin|caricature|affiche|logo)\b/.test(t)) return 'image';
 if (/^(une?\s+)?(video|animation|clip)\b/.test(t)) return 'video';
 return null;
}

// In an image-oriented conversation, users often type a visual description
// directly without writing "génère une image". This helper is deliberately
// content-neutral: it only detects whether a sentence looks like a visual
// brief. It does not alter, soften or filter the prompt itself.
function implicitVisualGenerationRequest(text) {
 const t=text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
 if (!t) return null;
 // Questions / conversational requests stay in chat even inside a photo profile.
 if (/\?|\b(explique|pourquoi|comment|parle(?:-moi)?|raconte|resume|resumer|analyse|analyser|avis|conseil|aide|qui|quand|ou|combien|que penses|qu['’]est)\b/.test(t)) return null;
 const visualSubject=/\b(femmes?|hommes?|personnes?|personnages?|visages?|corps|silhouettes?|modeles?|mannequins?|animaux?|chats?|chiens?|voitures?|motos?|maisons?|batiments?|paysages?|forets?|montagnes?|plages?|villes?|rues?|scenes?|decors?|objets?|produits?|robots?|creatures?)\b/.test(t);
 const visualCue=/\b(vu(?:e)?\s+de\s+(?:face|dos|profil)|face\s+camera|plein\s+pied|portrait|gros\s+plan|grand\s+angle|camera|objectif|eclairage|lumiere|studio|cinematographique|realiste|photorealiste|anime|illustration|dessin|debout|assis(?:e)?|allonge(?:e)?|marche|court|pose|porte|vetu(?:e)?|habille(?:e)?|rouge|bleu|vert|noir|blanc|dans|devant|derriere|sur|sous|avec)\b/i.test(t);
 const startsLikeBrief=/^(une?|un|des|ce|cette|femme|homme|personne|personnage|visage|corps|silhouette|modele|mannequin|chat|chien|voiture|moto|maison|paysage|scene|objet|produit|robot|creature)\b/.test(t);
 return visualSubject && (visualCue || startsLikeBrief) ? 'image' : null;
}
if (typeof module !== 'undefined') module.exports={explicitGenerationRequest,implicitVisualGenerationRequest};
