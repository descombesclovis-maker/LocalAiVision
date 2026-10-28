"""Curated OpenStreetMap professional categories used for bounded map prospecting.
All category tag keys and values are server-controlled (never interpolate user tags).
"""
from __future__ import annotations

SECTORS = [
 ("commerce","Commerces",[
  ("bakery","Boulangerie", "shop","bakery"),("butcher","Boucherie","shop","butcher"),
  ("pastry","Pâtisserie","shop","pastry"),("confectionery","Confiserie","shop","confectionery"),
  ("florist","Fleuriste","shop","florist"),("clothes","Prêt-à-porter","shop","clothes"),
  ("shoes","Chaussures","shop","shoes"),("jewelry","Bijouterie","shop","jewelry"),
  ("furniture","Mobilier","shop","furniture"),("gift","Cadeaux","shop","gift"),
  ("books","Librairie","shop","books"),("optician","Opticien","shop","optician"),
  ("electronics","Électronique","shop","electronics"),("computer","Informatique","shop","computer"),
  ("mobile_phone","Téléphonie","shop","mobile_phone"),("sports","Équipements sportifs","shop","sports"),
  ("bicycle","Cycles","shop","bicycle"),("outdoor","Outdoor et randonnée","shop","outdoor"),
  ("pet","Animalerie","shop","pet"),("pet_grooming","Toilettage animalier","shop","pet_grooming"),
  ("supermarket","Supermarché","shop","supermarket"),("convenience","Épicerie","shop","convenience"),
  ("wine","Caviste","shop","wine"),("beverages","Boissons","shop","beverages"),
  ("car","Concession automobile","shop","car"),("car_repair","Garage automobile","shop","car_repair"),
  ("hardware","Quincaillerie","shop","hardware"),("garden_centre","Jardinerie","shop","garden_centre"),
  ("doityourself","Bricolage","shop","doityourself"),("kiosk","Kiosque","shop","kiosk"),
 ]),
 ("restauration","Restauration et hébergement",[
  ("restaurant","Restaurant","amenity","restaurant"),("cafe","Café","amenity","cafe"),
  ("fast_food","Restauration rapide","amenity","fast_food"),("bar","Bar","amenity","bar"),
  ("pub","Pub","amenity","pub"),("ice_cream","Glacier","amenity","ice_cream"),
  ("food_court","Halle gourmande","amenity","food_court"),("hotel","Hôtel","tourism","hotel"),
  ("guest_house","Maison d'hôtes","tourism","guest_house"),("hostel","Auberge","tourism","hostel"),
  ("camp_site","Camping","tourism","camp_site"),
 ]),
 ("bienetre","Beauté et bien-être",[
  ("hairdresser","Salon de coiffure","shop","hairdresser"),
  ("beauty","Institut de beauté","shop","beauty"),("massage","Massages","shop","massage"),
  ("tattoo","Tatouage","shop","tattoo"),("cosmetics","Cosmétiques","shop","cosmetics"),
  ("perfumery","Parfumerie","shop","perfumery"),("spa","Spa","leisure","spa"),
  ("sauna","Sauna","leisure","sauna"),("fitness_centre","Salle de sport","leisure","fitness_centre"),
 ]),
 ("sante","Santé et services",[
  ("pharmacy","Pharmacie","amenity","pharmacy"),("doctors","Médecin","amenity","doctors"),
  ("dentist","Dentiste","amenity","dentist"),("veterinary","Vétérinaire","amenity","veterinary"),
  ("physiotherapist","Kinésithérapie","healthcare","physiotherapist"),
  ("psychotherapist","Psychothérapie","healthcare","psychotherapist"),
  ("clinic","Clinique","amenity","clinic"),("bank","Banque","amenity","bank"),
  ("post_office","Bureau de poste","amenity","post_office"),
 ]),
 ("services","Services professionnels",[
  ("estate_agent","Agence immobilière","office","estate_agent"),
  ("insurance","Assurance","office","insurance"),("lawyer","Avocat","office","lawyer"),
  ("accountant","Comptabilité","office","accountant"),("consulting","Conseil","office","consulting"),
  ("it","Services informatiques","office","it"),("advertising_agency","Publicité","office","advertising_agency"),
  ("architect","Architecte","office","architect"),
  ("travel_agent","Agence de voyages","shop","travel_agency"),
  ("copyshop","Imprimerie/reprographie","shop","copyshop"),
  ("laundry","Blanchisserie","shop","laundry"),("dry_cleaning","Pressing","shop","dry_cleaning"),
 ]),
 ("artisans","Artisanat et bâtiment",[
  ("electrician","Électricien","craft","electrician"),("plumber","Plombier","craft","plumber"),
  ("carpenter","Menuisier","craft","carpenter"),("roofer","Couvreur","craft","roofer"),
  ("painter","Peintre en bâtiment","craft","painter"),
  ("mason","Maçon","craft","mason"),("gardener","Paysagiste","craft","gardener"),
  ("photographer","Photographe","craft","photographer"),
  ("tailor","Tailleur","craft","tailor"),("jeweller","Artisan bijoutier","craft","jeweller"),
  ("pottery","Céramiste","craft","pottery"),("brewery","Brasserie artisanale","craft","brewery"),
 ]),
 ("loisirs","Loisirs, culture et tourisme",[
  ("museum","Musée","tourism","museum"),("gallery","Galerie d'art","tourism","gallery"),
  ("cinema","Cinéma","amenity","cinema"),("theatre","Théâtre","amenity","theatre"),
  ("dance","École de danse","leisure","dance"),("sports_centre","Centre sportif","leisure","sports_centre"),
  ("escape_game","Escape game","leisure","escape_game"),
  ("attraction","Attraction touristique","tourism","attraction"),
 ]),
 ("formation","Enseignement",[
  ("school","École","amenity","school"),("college","Collège","amenity","college"),
  ("university","Université","amenity","university"),("kindergarten","Crèche","amenity","kindergarten"),
  ("driving_school","Auto-école","amenity","driving_school"),
  ("music_school","École de musique","amenity","music_school"),
 ])
]
ALL={"all":{"id":"all","name":"Tous les métiers","group":"Général","tag":None,"value":None}}
for group,heading,items in SECTORS:
    for ident,label,tag,value in items:
        ALL[ident]={"id":ident,"name":label,"group":heading,"tag":tag,"value":value}
# Avoid inserting any user-supplied tag into Overpass statements.
GROUPS=[{"label":"Tous les métiers","items":[ALL["all"]]}]+[
 {"label":label,"items":[ALL[item[0]] for item in items]} for _,label,items in SECTORS
]

def category(category_id):
    key=str(category_id or "all").strip()
    if key not in ALL:
        raise ValueError("Métier inconnu. Choisis une catégorie dans la liste.")
    return ALL[key]

def catalog():
    return {"groups":GROUPS,"count":len(ALL)-1}
