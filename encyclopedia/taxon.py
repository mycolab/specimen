import os
import csv
import etcd
import json
import hashlib
import zipfile
import pandas as pd
import urllib.parse
import urllib.request

E_FILE = '/tmp/mycopedia.json'
MYCOBANK = {
    'url': os.environ.get('MYCOBANK_URL', 'https://www.mycobank.org/images/MBList.zip'),
    'zip': os.environ.get('MYCOBANK_ZIP', '/tmp/MBList.zip'),
    'xls': os.environ.get('MYCOBANK_XLS', '/tmp/MBList.xlsx'),
    'csv': os.environ.get('MYCOBANK_CSV', '/tmp/MBList.csv'),
    'tmp': os.environ.get('MYCOBANK_TMP', '/tmp')
}

ETCD_HOST = os.environ.get('ETCD_HOST', '127.0.0.1')
ETCD_PORT = os.environ.get('ETCD_PORT', 2379)


def etc_client() -> etcd.Client:
    client = etcd.Client(host=ETCD_HOST, port=ETCD_PORT)
    return client


def get_id(d: dict, lower: bool = True) -> str:
    """
    Generate Id from hash of dictionary
    :param d:
    :param lower:
    :return:
    """
    d_str = json.dumps(d)
    if lower:
        d_str = d_str.lower()

    return hashlib.md5(d_str.encode('utf-8')).hexdigest()


def write_json(data, file: str, indent: int = 4):
    """
    Write JSON file from dict
    :param data:
    :param file:
    :param indent:
    :return:
    """

    with open(file, 'w') as f:
        json.dump(data, f, indent=indent)


def expand_rank(abbr: str) -> str:
    """
    Expand taxon rank abbreviation
    :param abbr: taxon rank abbreviation
    :return: taxon rank
    """

    #  Primary Taxonomic Ranks
    #  ---------------------------
    #  kingdom -> phylum -> class -> order -> family -> genus -> species

    #  Extended Taxonomic Ranks [1]
    #  ---------------------------------
    #  Primary     Secondary
    #  -------     ---------
    #  kingdom
    #              subkingdom
    #  phylum
    #              subphylum
    #  class
    #              subclass
    #  order
    #              suborder
    #  family
    #              subfamily
    #              tribe
    #              subtribe
    #  genus
    #              subgenus
    #              section
    #              subsection
    #              series
    #              subseries
    #  species
    #              subspecies
    #              variety
    #              subvariety
    #              form
    #              subform
    # ---------------------------
    #
    # 1. reference: https://www.iapt-taxon.org/historic/2018.htm (Article 4)

    # Extended Taxonomic Rank Abbreviations (alphabetical) [mycobank.org]
    #   Abbreviation  Meaning          Transliteration
    rank_abbr = {
        '?':          'unknown',       # parse error: e.g. "Agaricus cinnamomeus δ croceus"
        '*':          'variety',       # archaic: subdivision of species ~= variety
        'cl.':        'class',         # classis ≡ class
        'div.':       'phylum',        # divisio ≡ division ≡ phylum
        'f.':         'form',          # forma ≡ form
        'f.sp.':      'variety',       # archaic: forma species ≡ species form ~= variety
        'fam.':       'family',        # familia ≡ family
        'gen.':       'genus',         # genus
        'ordo':       'order',         # ordo ≡ order
        'race':       'variety',       # archaic: race ~= variety
        'regn.':      'kingdom',       # regnum ≡ kingdom
        'sect.':      'section',       # section
        'ser.':       'series',        # series
        'sp.':        'species',       # species
        'stirps':     'genus',         # archaic: subdivision of Family ~= genus
        'subcl.':     'subclass',      # subclassis ≡ subclass
        'subdiv.':    'subphylum',     # subdivisio ≡ subdivision ≡ subphylum
        'subdivF.':   'species',       # archaic: subdivision of genus (i.e. species)
        'subf.':      'subform',       # subforma ≡ subform
        'subfam.':    'subfamily',
        'subgen.':    'subgenus',
        'subordo':    'suborder',      # subordo ≡ suborder
        'subregn.':   'subkingdom',    # subregnum ≡ subkingdom
        'subsect.':   'subsection',
        'subser.':    'subseries',
        'subsp.':     'subspecies',
        'subtr.':     'subtribe',
        'subvar.':    'subvariety',    # subvarietas ≡ subvariety
        'tr.':        'tribe',
        'var.':       'variety'
    }

    rank = rank_abbr.get(abbr, abbr)

    return rank


def mycobank_to_csv():
    # write 'MBfile.xlsx' excel to csv
    data = pd.read_excel(MYCOBANK.get('xls'))
    data.to_csv(MYCOBANK.get('csv'), index=None, header=True)
    os.remove(MYCOBANK.get('xls'))


def download_mycobank():
    # download mycobank 'MBfile.zip'
    urllib.request.urlretrieve(MYCOBANK.get('url'), MYCOBANK.get('zip'))
    with zipfile.ZipFile(MYCOBANK.get('zip'), 'r') as zip_ref:
        zip_ref.extractall(MYCOBANK.get('tmp'))
    os.remove(MYCOBANK.get('zip'))


def load_mycobank_taxons() -> list:
    h = {
        'link_id': 0,
        'name': 1,
        'author': 2,
        'rank': 3,
        'year': 4,
        'status': 5,
        'mycobank_id': 6,
        'link': 7,
        'classification': 8,
        'current_name': 9
    }

    taxons = []

    if not os.path.exists(MYCOBANK.get('csv')):
        if not os.path.exists(MYCOBANK.get('xls')):
            download_mycobank()
        mycobank_to_csv()

    with open(MYCOBANK.get('csv'), mode='r') as f:
        cols = csv.reader(f)
        skip = True
        for col in cols:
            # skip header record
            if skip:
                skip = False
                continue
            # 'link': col[h['link']]
            taxon = {
                'link_id': col[h['link_id']],
                'mycobank_id': col[h['mycobank_id']],
                'name': col[h['name']],
                'rank': col[h['rank']],
                'status': col[h['status']],
                'classification': col[h['classification']],
            }
            taxons.append(taxon)

    return taxons


def load_encyclopedia() -> list:
    encyclopedia = []
    mycobank_taxons = load_mycobank_taxons()

    # process mycobank taxons
    for taxon in mycobank_taxons:

        mycobank_id = taxon.get('mycobank_id')
        name = str(taxon.get('name'))
        key_name = '.'.join(name.split()).lower()
        status = taxon.get('status')

        if status != 'Legitimate':
            continue

        rank = expand_rank(taxon.get('rank'))
        if 'rank' == 'unknown':
            continue

        classification = taxon.get('classification').replace(' ', '').split(',')

        # url
        link_id = taxon.get('link_id')
        link_path = urllib.parse.quote(f'www.mycobank.org/page/Name details page/{link_id}')
        url = f'https://{link_path}'

        # create initial taxonomy
        taxonomy = {
            'name': name,
            'rank': rank,
        }

        # get Id before adding classification
        entry_id = get_id(taxonomy)

        # update taxonomy with classification
        taxonomy.update({'classification': classification})

        entry = {
            'id': entry_id,
            'key_name': key_name,
            'taxonomy': taxonomy,
            'references': {
                'mycobank': {
                    'id': mycobank_id,
                    'url': url
                }
            }
        }

        encyclopedia.append(entry)

    return encyclopedia


def write_encyclopedia(encyclopedia: list):
    if not os.path.exists(E_FILE):
        write_json(encyclopedia, E_FILE)


if __name__ == '__main__':
    mycopedia = load_encyclopedia()
    write_encyclopedia(mycopedia)





