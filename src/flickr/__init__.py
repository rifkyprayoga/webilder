import flickrapi
import re
import urllib
from datetime import date

API_KEY = '045379bc5368502f749af23d95a17c83'

flickr = flickrapi.FlickrProxy(api_key = API_KEY)

def get_download_list(config):
    if not config.get('flickr.enabled'):
        return []
    rules = config.get('flickr.rules')
    images = []
    all_photos = []
    for rule in rules:
        for tag_term in rule['tags'].split(';'):
            tag_term = ','.join([tag.strip() for tag in tag_term.split(',')])
            params_dict = dict(per_page=25)
            if tag_term:
                params_dict['tags'] = tag_term
                params_dict['tag_mode'] = 'all'

            user_id = rule['user_id'].strip()
            if user_id:
                if 'nsid' not in rule:
                    rule['nsid'] = flickr.get_user_nsid(user_id)
                    config.save_config()
                params_dict['user_id'] = rule['nsid']

            photos = flickr.photos_search(**params_dict)
            for photo in photos:
                photo._album = rule['album']
            all_photos.extend(photos)

    if config.get('flickr.download_interesting'):
        photos = flickr.interestingness_search(per_page=25)
        for photo in photos:
            photo._album = 'Interestingness - '+date.today().strftime('%B %Y')
        all_photos.extend(photos)

    for photo in all_photos:
        title = photo.title
        id = str(photo.photo_id)
        images.append({
            'name': 'flickr_%s.jpg' % id,
            'title': title,
            'data': {
                'photo': photo,
                'album': photo._album,
            }});
    return images

def fetch_photo_info(config, photo):
    photo_obj = photo['data']['photo']
    photo['data']['info'] = photo_obj.get_info()
    if config.get('filter.only_landscape'):
        photo['data']['aspect_ratio'] = photo_obj.get_aspect_ratio()

def get_photo_stream(config, photo):
    stream = urllib.urlopen(photo['data']['info']['image_url'])
    return stream

def process_photo(config, photo, f):
    info = photo['data']['info']
    metadata = {
            'albumTitle': photo['data']['album'],
            'title': info['title'],
            'credit': info['owner'],
            'url': info['url'],
            'tags': ' '.join(info['tags'])
            }
    return f.read(), metadata

