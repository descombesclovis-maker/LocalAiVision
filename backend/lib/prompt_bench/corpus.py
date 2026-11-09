"""V2-B reproducible corpus. Each item lists the explicit requirements that MUST survive preparation.

`must` : substrings (accent/case-insensitive) that must appear in every prepared prompt.
`forbidden` : terms that must not be ADDED by preparation (flagged only if absent from the source).
"""

CORPUS: tuple[dict, ...] = (
    {
        "id": "photo_portrait", "task": "photo",
        "prompt": "Portrait réaliste d'une femme d'environ 35 ans, cheveux châtain clair attachés, yeux verts, "
                  "pull en laine bordeaux, lumière de fenêtre douce venant de la gauche, fond gris clair uni. "
                  "Peau naturelle avec pores visibles, sans retouche excessive.",
        "must": ["bordeaux", "yeux verts", "de la gauche", "pores visibles", "sans retouche excessive"],
        "forbidden": ["rouge", "lisse", "plastique"],
    },
    {
        "id": "photo_product", "task": "photo",
        "prompt": "Photographie produit d'un flacon de parfum en verre transparent bleu cobalt, bouchon doré posé "
                  "à droite, sur une table en marbre blanc, fond beige, reflets nets sur le verre, aucune étiquette visible.",
        "must": ["cobalt", "doré", "à droite", "aucune étiquette visible"],
        "forbidden": ["rouge", "noir"],
    },
    {
        "id": "photo_spatial_product", "task": "photo",
        "prompt": "Un flacon de parfum bleu au centre avec son bouchon doré posé séparément à droite, sur une surface en marbre blanc.",
        "must": ["bleu", "doré", "séparément", "à droite", "marbre blanc"],
        "forbidden": ["rouge", "noir"],
    },
    {
        "id": "photo_multi_objects", "task": "photo",
        "prompt": "Une table en bois avec trois objets : une tasse rouge à gauche, un livre bleu au centre, et une plante verte à droite. "
                  "La tasse rouge est devant le livre bleu. Pas de personne dans l'image.",
        "must": ["tasse rouge", "livre bleu", "plante verte", "à gauche", "au centre", "à droite", "devant le livre bleu", "pas de personne"],
        "forbidden": ["jaune", "orange"],
    },
    {
        "id": "photo_spatial", "task": "photo",
        "prompt": "Un chat noir assis sur le rebord d'une fenêtre, derrière lui une pluie de fond floue ; le chat regarde vers la gauche. "
                  "Le chat ne doit pas être blanc.",
        "must": ["chat noir", "rebord", "derrière lui", "vers la gauche", "ne doit pas être blanc"],
        "forbidden": ["orange", "tigré"],
    },
    {
        "id": "t2v_camera_fixed", "task": "text-to-video",
        "prompt": "Plan fixe, caméra immobile sur un trépied. Une voiture noire traverse lentement le cadre de gauche à droite "
                  "sur une route de montagne au petit matin. Pas de travelling, pas de zoom.",
        "must": ["caméra immobile", "voiture noire", "de gauche à droite", "pas de travelling", "pas de zoom"],
        "forbidden": ["dolly", "panoramique", "rouge"],
    },
    {
        "id": "t2v_complex_motion", "task": "text-to-video",
        "prompt": "Une danseuse en robe blanche fait trois tours sur elle-même puis lève le bras droit, pendant que la caméra "
                  "fait un lent travelling avant. Les pieds restent en contact avec le sol.",
        "must": ["robe blanche", "trois tours", "bras droit", "travelling avant", "pieds restent en contact"],
        "forbidden": ["zoom arrière", "panoramique", "rouge"],
    },
    {
        "id": "i2v_identity", "task": "image-to-video",
        "prompt": "À partir de l'image fournie, l'homme en chemise bleue tourne légèrement la tête vers la droite et sourit. "
                  "Garder exactement le même visage, la même coiffure et la même chemise. Le fond ne doit pas changer.",
        "must": ["chemise bleue", "tourne légèrement la tête", "vers la droite", "même visage", "le fond ne doit pas changer"],
        "forbidden": ["lunettes", "barbe"],
    },
    {
        "id": "retouch_localized", "task": "retouch",
        "prompt": "Remplacer uniquement le ciel gris par un ciel bleu dégagé. Ne modifier ni le bâtiment, ni la route, ni les voitures.",
        "must": ["uniquement le ciel gris", "ciel bleu dégagé", "ni le bâtiment", "ni la route", "ni les voitures"],
        "forbidden": ["coucher de soleil", "orange"],
    },
    {
        "id": "ad_exact_text", "task": "advertising",
        "prompt": "Affiche publicitaire pour une marque de café, texte exact « Réveillez-vous » en grandes lettres noires en haut, "
                  "une tasse fumante au centre sur fond crème.",
        "must": ["Réveillez-vous", "grandes lettres noires", "en haut", "tasse fumante", "au centre"],
        "forbidden": ["starbucks", "rouge"],
    },
    {
        "id": "contradiction_light", "task": "photo",
        "prompt": "Une scène de nuit complètement sombre, mais avec un soleil de midi très lumineux au premier plan, "
                  "ciel totalement bleu sans nuages.",
        "must": ["nuit complètement sombre", "soleil de midi", "ciel totalement bleu"],
        "forbidden": ["lune"],
        "expect_conflict": True,
    },
    {
        # Long dense scene: constraints placed at the END, beyond the CLIP window (tests approach C).
        "id": "photo_dense_long", "task": "photo",
        "prompt": "Photographie éditoriale d'une boulangerie de quartier au lever du soleil. Au premier plan, une baguette "
                  "croustillante posée sur un comptoir en bois clair, puis derrière elle une vitrine avec des croissants dorés, "
                  "des tartes aux fraises et des muffins au chocolat. Sur la gauche, une femme âgée en tablier vert sourit en "
                  "rangeant des boîtes en carton blanches. Sur la droite, un vélo rouge est appuyé contre un mur de briques. "
                  "Le ciel visible par la porte est rose pâle. Lumière chaude du matin, profondeur de champ modérée. "
                  "Aucun texte ni enseigne lisible. Pas de personne supplémentaire au premier plan.",
        "must": ["baguette", "comptoir en bois clair", "croissants dorés", "tablier vert", "boîtes en carton blanches",
                 "vélo rouge", "mur de briques", "aucun texte ni enseigne lisible", "pas de personne supplémentaire"],
        "forbidden": ["bleu", "noir"],
    },
)

IMAGE_TASKS = frozenset({"photo", "retouch", "advertising"})
VIDEO_TASKS = frozenset({"text-to-video", "image-to-video"})
