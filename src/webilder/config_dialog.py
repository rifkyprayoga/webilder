from webilder import __version__
import urllib
import pygtk
import gtk
import os

from uitricks import UITricks, open_browser

from progress_dialog import *

class WebilderAgent(urllib.FancyURLopener):
    version = 'Webilder/%s' % __version__

# pygtk.require("2.0")

rotation_consts = {
    1: _('1 minute'),
    2: _('2 minutes'),
    5: _('5 minutes'),
    10: _('10 minutes'),
    20: _('20 minutes'),
    30: _('30 minutes'),
    60: _('1 hour'),
    120: _('2 hours'),
    240: _('4 hours'),
    24*60: _('1 day')}
quality_names = ['high', 'wide', 'low']

class ConfigDialog(UITricks):
    def __init__(self):
        UITricks.__init__(self, 'ui/config.glade', 'config_dialog')
        self.on_flickr_enabled__toggled()
        self.on_webshots_enabled__toggled()
        self.on_autodownload_bool__toggled()
        self.on_rotate_bool__toggled()
        self.on_wallpaper_use_script__toggled()

        cell = gtk.CellRendererToggle()
        cell.set_property('activatable', True)
        column = gtk.TreeViewColumn('', cell, active=3)
        self.flickr_rules.append_column(column)
        cell.connect('toggled', self.on_rule_toggled, 3)

        for index, value in enumerate([_('Album'), _('Tags'), _('User')]):
            cell = gtk.CellRendererText()
            cell.set_property('editable', True)
            column = gtk.TreeViewColumn(value, cell, text=index)
            column.set_resizable(True)
            self.flickr_rules.append_column(column)
            cell.connect('edited', self.on_cell_edited, index)

        cell = gtk.CellRendererCombo()
        cell.set_property('has-entry', False)
        combo_model = gtk.ListStore(str)
        combo_model.append(('Interestingness', ))
        combo_model.append((_('Date'), ))
        cell.set_property('model', combo_model)
        cell.set_property('text-column', 0)
        cell.set_property('editable', True)
        column = gtk.TreeViewColumn(_('Sort'), cell, text=4)
        self.flickr_rules.append_column(column)
        cell.connect('edited', self.on_cell_edited, 4)
        self.rotate_interval.get_model().clear()

        for time in sorted(rotation_consts.keys()):
            self.rotate_interval.append_text(rotation_consts[time])
        self.wallpaper_widgets = dict(gnome=self.wallpaper_use_gnome,
                kde=self.wallpaper_use_kde,
                script=self.wallpaper_use_script)
        self.notebook.drag_dest_set(gtk.DEST_DEFAULT_MOTION|gtk.DEST_DEFAULT_HIGHLIGHT|gtk.DEST_DEFAULT_DROP, [('text/plain', 0, 0), ('text/uri-list', 0, 1)], 
                gtk.gdk.ACTION_COPY|gtk.gdk.ACTION_MOVE)

    def on_notebook__drag_data_received(self, widget, context, x, y,
            selection, targetType, time):
        if targetType == 1:
            url = selection.data.split()[0]
        else:
            url = selection.data
        import urllib
        data = WebilderAgent().open(url).read()
        for channel in parse_cid_file(data):
            self.flickr_rules.get_model().append((channel['name'],channel['terms'],'', True, _('Interestingness')))
        flickr_pos = self.notebook.child_get(self.flickr_tab, 'position')[0]
        self.notebook.set_current_page(flickr_pos)

    def run_dialog(self, config):
        self.load_config(config)
        while 1:
            response = self.run()
            if response != 0:
                break

            cdir = self.collection_dir.get_text()
            if not os.path.exists(cdir):
                mb = gtk.MessageDialog(type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_YES_NO, message_format=
                    _("Collection directory %s does not exist. Would you like it to be created?") % cdir)
                mbval = mb.run()
                mb.destroy()
                if (mbval == gtk.RESPONSE_YES):
                    os.mkdir(cdir)
                else:
                    self.collection_dir.grab_focus()
                    continue

            if not os.path.isdir(cdir):
                mb = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK, message_format=_("%s is not a directory.") % cdir)
                mb.run()
                mb.destroy()
                self.collection_dir.grab_focus()
                continue
            
            self.update_config(config)
            config.save_config()
            break
        self._top.destroy()

    def load_config(self, config):
        # general tab
        self.rotate_bool.set_active(config.get('rotate.enabled'))
        interval = config.get('rotate.interval')
        if interval not in rotation_consts:
            if interval<=0:
                interval = 1
            interval = max([t for t in rotation_consts.keys() if t<=interval])
        interval = sorted(rotation_consts.keys()).index(interval)
        self.rotate_interval.set_active(interval)

        self.autodownload_bool.set_active(config.get('autodownload.enabled'))
        self.autodownload_interval.set_value(config.get('autodownload.interval'))


        # flickr tab
        self.flickr_enabled.set_active(config.get('flickr.enabled'))
        model = gtk.ListStore(str, str, str, bool, str)
        for rule in config.get('flickr.rules'):
            model.append((
                rule['album'], 
                rule['tags'], 
                rule['user_id'], 
                rule.get('enabled', True),
                rule.get('sort', 'Interestingness'),
                ))
        self.flickr_rules.set_model(model)
        self.flickr_download_interesting.set_active(config.get('flickr.download_interesting'))

        # webshots tab
        self.webshots_enabled.set_active(config.get('webshots.enabled'))
        self.webshots_username.set_text(config.get('webshots.username'))
        self.webshots_password.set_text(config.get('webshots.password'))
        quality = config.get('webshots.quality')
        if quality not in quality_names:
            quality = 'low'
        getattr(self, quality).set_active(True)

        # advanced tab
        self.collection_dir.set_text(config.get('collection.dir'))
        wallpaper_active_widget = self.wallpaper_widgets.get(
                config.get('webilder.wallpaper_set_method'), self.wallpaper_use_gnome)
        wallpaper_active_widget.set_active(True)
        self.script.set_text(config.get('webilder.wallpaper_script'))
        self.only_landscape.set_active(config.get('filter.only_landscape'))


    def update_config(self, config):
        # rotator tab
        config.set('rotate.enabled', self.rotate_bool.get_active())
        config.set('rotate.interval', sorted(rotation_consts.keys())[
            self.rotate_interval.get_active()])

        config.set('autodownload.enabled', self.autodownload_bool.get_active())
        config.set('autodownload.interval', self.autodownload_interval.get_value())

        # flickr tab
        config.set('flickr.enabled', self.flickr_enabled.get_active())
        rules = []
        for rule in self.flickr_rules.get_model():
            rules.append({'album': rule[0], 'tags': rule[1], 'user_id': rule[2], 'enabled': rule[3], 'sort': rule[4]})
        config.set('flickr.rules', rules)
        config.set('flickr.download_interesting', self.flickr_download_interesting.get_active())

        # webshots tab
        config.set('webshots.enabled', self.webshots_enabled.get_active())
        config.set('webshots.username', self.webshots_username.get_text())
        config.set('webshots.password', self.webshots_password.get_text())
        config.set('webshots.cookie', '')

        res = 'low'
        for q in quality_names:
            if getattr(self, q).get_active():
                res = q
        config.set('webshots.quality', res)

        # advanced tab
        config.set('collection.dir', self.collection_dir.get_text())
        use = 'gnome'
        for name, widget in self.wallpaper_widgets.iteritems():
            if widget.get_active():
                use = name
        config.set('webilder.wallpaper_set_method', use)
        config.set('webilder.wallpaper_script', self.script.get_text())
        config.set('filter.only_landscape', self.only_landscape.get_active())
        

    def on_rotate_bool__toggled(self, *args):
        self.rotate_interval.set_sensitive(self.rotate_bool.get_active())

    def on_autodownload_bool__toggled(self, *args):
        self.autodownload_interval.set_sensitive(self.autodownload_bool.get_active())

    def on_flickr_enabled__toggled(self, *args):
        for frame in (self.flickr_interestingness_frame, self.flickr_tags_frame):
            frame.set_sensitive(self.flickr_enabled.get_active())

    def on_webshots_enabled__toggled(self, *args):
        self.webshots_login_frame.set_sensitive(self.webshots_enabled.get_active())
        self.webshots_res_frame.set_sensitive(self.webshots_enabled.get_active())

    def on_wallpaper_use_script__toggled(self, *args):
        self.script.set_sensitive(self.wallpaper_use_script.get_active())

    def on_add__clicked(self, widget):
        iter = self.flickr_rules.get_model().append([_('Album Name'),'tag1,tag2','', True, 'Interestingness'])
        # self.flickr_rules.scroll_to_cell(path)
        
    def on_remove__clicked(self, widget):
        model, iter = self.flickr_rules.get_selection().get_selected()
        if iter:
            model.remove(iter)

    def on_flickr_rules__selection_changed(self, *args):
        self.remove.set_sensitive(
                self.flickr_rules.get_selection().get_selected()[1] is not None)

    def on_cell_edited(self, cell, path, new_text, data):
        if data==1:
            terms = new_text.split(';')
            terms = [[tag.strip() for tag in term.split(',')] for term in terms]
            new_text = ';'.join([', '.join([tag for tag in term]) for term in terms])
        if data==0:
            new_text = new_text.strip()
            if not new_text:
                new_text = 'Untitled Album'

        self.flickr_rules.get_model()[path][data] = new_text

    def on_rule_toggled(self, cell, path, column):
        self.flickr_rules.get_model()[path][column] = not self.flickr_rules.get_model()[path][column]

    def on_directory_browse__clicked(self, sender):
        fs = gtk.FileChooserDialog(action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
                buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_OK,gtk.RESPONSE_OK))
        if fs.run()==gtk.RESPONSE_OK:
            self.collection_dir.set_text(fs.get_filename())
        fs.destroy()

    def on_tips__clicked(self, widget):
        text = _("""
        Getting started with flickr is easy.

        Press the 'Add' button. Changing the tags to
        <b>party,beach</b> (or anything that you want).
        will bring you photos that are tagged with both
        <b>party</b> and <b>beach</b>.

        You can write: <b>party,beach;swimsuit</b>
        if you want photos tagged with both 
        <b>party</b> and <b>beach</b>, or with <b>swimsuit</b>.
        
        If you want to get photos of a specific flickr user, 
        just write his username in the <i>User</i> column, 
       otherwise leave this column blank.

        The album name can be anything meaningful to you, 
        for example "Beach Parties".

        To get the best photos it is best to leave the sort
        column with 'Interestingness'. This will download only
        the most interesting photos. The other option 'Date',
        will make Webilder to download most recent photos.
        """)
        mb = gtk.MessageDialog(type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_OK)
        
        mb.set_markup(text)
        mbval = mb.run()
        mb.destroy()

    def on_flickr_recommend__clicked(self, widget):
        recommend_dialog = ProgressDialog(text=_('Sending your recommendations...'))
        rules = list(self.flickr_rules.get_model())
        class RecommendingThread(ProgressThread):
            @progress_thread_run
            def run(self):
                import urllib
                recommend = [rule for rule in rules if (not rule[2]) or (not rule[3])]
                size = len(recommend)
                for index, rule in enumerate(recommend):
                    if self.should_terminate():
                        break
                    album, terms = rule[0], rule[1]
                    data = urllib.urlencode({'name': album, 'terms': terms})
                    self.status_notify(float(index)/size, 
                            progress_text=_('Sending rule %d of %d') % (index+1, size))
                    try:
                        rsp = WebilderAgent().open('http://api.webilder.org/submit_channel', data).read()
                    except e:
                        print str(e)
                else:
                    self.status_notify(1.0, progress_text='Done')
                    self.safe_message_dialog(_('Thank you for recommending your albums!'), gtk.MESSAGE_INFO)

        thread=RecommendingThread(recommend_dialog)
        thread.start()
        recommend_dialog._top.run()

    def on_flickr_get_more_albums__clicked(self, widget):
        url = 'http://www.webilder.org/channels/'
        open_browser(url = url,
                no_browser_title = _('Could not open browser'),
                no_browser_markup = _('Webilder was unable to find a browser, please visit: \n'
                '%s') % url)

def parse_cid_file(data):
    from xml.dom.minidom import parseString
    dom = parseString(data)
    channel_nodes = dom.getElementsByTagName('channel')
    channels = []
    for channel in channel_nodes:
        terms = []
        for term in dom.getElementsByTagName('term'):
            tag_list = []
            for tag in term.getElementsByTagName('tag'):
                tag_list.append(tag.attributes['name'].value)
            terms.append(', '.join(tag_list))
        terms = '; '.join(terms)
        name = channel.attributes['name'].value
        channels.append(dict(name=name, terms=terms))
    return channels
