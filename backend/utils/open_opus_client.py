import requests
from typing import TypedDict

def get_composers():
    COMPOSERS_URL = 'https://api.openopus.org/composer/list/pop.json'
    result = requests.request('GET', COMPOSERS_URL)
    data = result.json()
    composers = data['composers']
    cmps = {}
    for composer in composers:
        id = composer['id']
        name = composer['name']
        cmps[id] = name
    return cmps

def get_works(composer_id):
    WORKS_URL = f'https://api.openopus.org/work/list/composer/{composer_id}/genre/all.json'
    result = requests.request('GET', WORKS_URL)
    data = result.json()
    works = data['works']
    work_titles = []
    for work in works:
        work_titles.append(work['title'])
        break
    return work_titles




composers = get_composers()
all_works = {}
for id, name in composers.items():
    works = get_works(composer_id=id)
    all_works[name] = works

print(all_works)
