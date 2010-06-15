import os, time

#Gettext Support
import gettext
gettext.install('webilder')

class ConfigObject:
    def __init__(self, file=None):
        self._dict = dict(DEFAULT_CONFIG)
        self._dirty_keys = set()
        if file:
            if os.path.exists(file):
                self.load_config(file)
            else:
                self._filename = file

        if not os.path.exists(os.path.dirname(file)):
            os.mkdir(os.path.dirname(file))
            os.mkdir(self.get('collection.dir'))
            self.save_config(file);

        if not os.path.isdir(self.get('collection.dir')):
            raise ValueError, _("collection.dir is set to a non-directory, check your config file.")

    def get(self, key, *args):
        return self._dict.get(key, *args)

    def set(self, key, value):
        self._dirty_keys.add(key)
        self._dict[key] = value

    def load_config(self, file):
        self._filename = file
        f = open(file, 'r')
        for lineno, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            index = line.find('=')
            if index<0:
                raise ValueError(_('Error parsing line %d of config file %s') % (lineno, file))
            key, value = line[:index].strip(), line[index+1:].strip()
            if key in self._dict:
                try:
                    self._dict[key] = eval(value)
                except:
                    if key == 'webilder.installation_date' and value.startswith('time.struct_time'):
			# repr(time.localtime()) stopped looking like a tuple in Python 2.6
			self._dict[key] = time.localtime()[:3]
                    else:	
                        raise ValueError(_('Error parsing line %d of config file %s') % (lineno, file))
            else:
                raise ValueError(_('Unrecognized key in line %d of config file %s') % (lineno, file))
        f.close()

    def save_config(self, file=None):
        if not file:
            file = self._filename
        org_cfg = ConfigObject(file)
            
        f = open(file, 'w')
        for key,v in DEFAULT_CONFIG:
            try:
                if key in self._dirty_keys:
                    value = self._dict[key]
                else:
                    value = org_cfg.get(key, None)
                f.write('%s = %r\n' % (key, value))
            except e:
                f.write('# '+str(e))
        f.close()
        self._dirty_keys.clear()

DEFAULT_CONFIG = [
    ('collection.dir', os.path.expanduser('~/.webilder/Collection')),
    ('rotate.enabled', True),
    ('rotate.interval', 5),

    ('webshots.enabled', False),
    ('webshots.auto_download', True),
    ('webshots.username', ''),
    ('webshots.password', ''),
    ('webshots.quality', 'low'),
    ('webshots.cookie', ''),

    ('flickr.enabled', True),
    ('flickr.auto_download', True),
    ('flickr.rules', []),
    ('flickr.download_interesting', True),
    ('flickr.scale_down', (1600, 1200)),

    ('autodownload.enabled', True),
    ('autodownload.interval', 24),
    ('autodownload.last_time', None),
    ('webilder.layout', {}),
    ('webilder.wallpaper_set_method', 'gnome'),
    ('webilder.wallpaper_script', ''),
    ('webilder.installation_date', time.localtime()[:3]),
    ('webilder.stats', dict(downloads=0, rotations=0)),
    ('filter.only_landscape', False)]

DEFAULT_CONFIG_FILE = os.path.expanduser('~/.webilder/webilder.conf')

config = ConfigObject(DEFAULT_CONFIG_FILE)

def reload_config():
    config.load_config(DEFAULT_CONFIG_FILE)
     
def set_wallpaper(filename):
    use = config.get('webilder.wallpaper_set_method')
    if use=="gnome":
        import gconf
        conf_client = gconf.client_get_default()
        conf_client.set_string('/desktop/gnome/background/picture_filename', 
            filename)
    elif use=="kde":
        script = 'dcop kdesktop KBackgroundIface setWallpaper "%f" 4'
        script = script.replace('%f', filename)
        os.popen2(script)
    elif use=="script":
        script = config.get('webilder.wallpaper_script')
        script = script.replace('%f', filename)
        os.popen2(script)
    stats = config.get('webilder.stats')
    stats['rotations'] += 1
    config.set('webilder.stats', stats)
    config.save_config()
