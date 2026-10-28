"""Conservative public-data filter for *small, apparently independent* leads.

These rules reduce large chains and industrial companies; they never certify
independence, workforce size or absence of a website without corroboration.
"""
import re
import unicodedata

# Recognisable national/international chains. Word boundaries avoid filtering a
# totally different business that only contains part of a chain name.
CHAINS=(
    "auchan","picard","maxi zoo","gifi","carrefour","carrefour market",
    "carrefour city","e leclerc","leclerc","intermarche","netto","lidl",
    "aldi","monoprix","franprix","casino supermarches","super u",
    "hyper u","u express","action","b&m","b m","la foir fouille",
    "ikea","but","conforama","fnac","darty","boulanger","cultura",
    "decathlon","intersport","go sport","sport 2000","kiabi","primark",
    "zara","h&m","uniqlo","mango","celio","jules","cache cache",
    "sephora","nocibe","marionnaud","yves rocher","rituals",
    "leroy merlin","castorama","brico depot","mr bricolage","weldom",
    "gamm vert","jardiland","truffaut","animalis","botanic",
    "macdonald","mcdonalds","mcdonald's","burger king","kfc","quick","subway",
    "starbucks","dominos pizza","pizza hut","buffalo grill",
    "courtepaille","flunch","paul","brioche doree","la mie caline",
    "basic fit","fitness park","keep cool","orange","sfr",
    "bouygues telecom","free center","norauto","feu vert",
    "midas","speedy","point s","euromaster","cash converters",
    "easy cash","cash express","electro depot","noz","stockomani",
    "grand frais","biocoop","naturalia","la vie claire",
    "optical center","afflelou","krys","atol","optic 2000",
)
# Reject cases where a brand begins a storefront label. A suffix such as
# a locality or a shopping-center name is common for chains.
def normalize(value):
    plain=unicodedata.normalize("NFKD",str(value or "").casefold())
    plain="".join(ch for ch in plain if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+"," ",plain).strip()

_CHAIN_NORMALIZED=tuple(sorted({normalize(n) for n in CHAINS},key=len,reverse=True))
_EXCLUDED_ACTIVITY={
    "supermarket","department store","mall","wholesale","warehouse",
    "trade","industrial","factory","storage rental","distribution centre",
}
# Official French employee bracket codes: 11 = 10–19; 12 = 20–49.
_SMALL_BRACKETS={"00","01","02","03","11","NN",""}
_BIG_SIZES={"ETI","GE","GRANDE ENTREPRISE","GRANDE_ENTREPRISE","LARGE"}
_EXCLUDED_NAF_PREFIX=("46.","47.30","64.","65.","66.")


def eligible(row):
    """Candidate with no *recorded* business website, no known chain/large scale.

    Missing site data must still be labelled 'not listed', not 'no site'.
    Unknown company size is tolerated and must not be declared verified.
    """
    if not isinstance(row,dict) or not row.get("name"):
        return False
    if row.get("website") or row.get("website_recorded"):
        return False
    if normalize(row.get("company_size")).upper().replace(" ","_") in {
            "ETI","GE","GRANDE_ENTREPRISE","LARGE"}:
        return False
    bracket=str(row.get("workforce_band") or "").upper().strip()
    if bracket not in _SMALL_BRACKETS:
        return False
    try:
        if int(row.get("establishment_count") or 0)>3:
            return False
    except (TypeError,ValueError):
        pass
    category=normalize(row.get("osm_category") or row.get("category"))
    if category in _EXCLUDED_ACTIVITY:
        return False
    naf=str(row.get("naf_code") or row.get("osm_category") or "").strip()
    if any(naf.startswith(start) for start in _EXCLUDED_NAF_PREFIX):
        return False
    labels=[normalize(row.get(field)) for field in ("name","brand","operator","network")]
    for label in labels:
        if not label:continue
        for chain in _CHAIN_NORMALIZED:
            if label==chain or label.startswith(chain+" "):
                return False
    return True
