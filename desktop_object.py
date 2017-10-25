import os
import urllib.parse

class DesktopObject(object):

    DESKTOP_KEYS = [
        'Version',
        'Name',
        'Comment',
        'Type',
        'Exec',
        'TryExec',
        'Icon',
        'Categories',
        'StartupWMClass',
        'X-Endless-LaunchMaximized',
        'X-Endless-SplashBackground'
    ]
        
    def __init__(self, data):
        self._locale_keys = ['Name', 'Comment']
        self._suffix = '.desktop.in'
        self._data = data

        self.defaults = {}
        self.defaults['Version'] = '1.0'
        self.defaults['Type'] = 'Application'
        self.defaults['StartupWMClass'] = None

    def get(self, key):
        if key in self.json_keys:
            val = self._data[self.json_keys[key]]
            if key == 'Icon':
                return self._icon_prefix + val
            if key == 'TryExec':
                if not val:
                    # Convert empty string to None to avoid writing field
                    return None
                return val
            if key == 'Categories':
                if val is None:
                    return ''
                categories = ';'.join(val.split(' and '))
                if not categories.endswith(';'):
                    categories += ';'
                return categories
            if key == 'X-Endless-LaunchMaximized':
                # In the CMS, the splash screen type serves a double duty:
                # if the type is 'None', we don't launch maximized
                if val in ['Default', 'Custom']:
                    return 'true'
                else:
                    return 'false'
            if key == 'X-Endless-SplashBackground':
                if val:
                    return val
                else:
                    return None
            else:
                return val
        elif key in self.defaults:
            return self.defaults[key]
        elif key == 'Position':
            folder = self.get('Folder')
            index = self.get('Index')
            if folder == 'none' or folder == '' or index is None:
                return None
            elif folder == 'desktop' or folder == 'default':
                return index
            else:
                return folder + ':' + index
        else:
            raise AttributeError

    def write_key(self, handle, key):
        val = self.get(key)
        if val is not None:
            line = '%s=%s\n' % (key, val)
            if self.key_is_localized(key):
                line = '_' + line

            handle.write(line)
    
    def key_is_localized(self, key):
        return key in self._locale_keys

    def get_desktop_path(self):
        return os.path.join(self.get_desktop_dir(),
                            self._prefix + self.get('Id') + self._suffix)

class LinkObject(DesktopObject):

    json_keys = {
        'Name': 'linkName',
        'Comment': 'linkSubtitle',
        'Categories': 'linkCategory',
        'Id': 'linkId',
        'Icon': 'linkId',
        'URL': 'linkUrl',
        'Index': 'linkDesktopPosition',
        'Folder': 'linkFolder'
    }

    def __init__(self, data, desktop_dir, locale):
        super(LinkObject, self).__init__(data)
        self._desktop_dir = desktop_dir
        self._default_name = self._data['linkName']
        self._name_locales = []
        self._localized_names = {}
        self._default_url = self.get('URL')
        self._url_locales = []
        self._localized_urls = {}
        self._prefix = 'eos-link-'
        self._icon_prefix = 'eos-link-'

        # Read the list of links to turn into web apps
        with open('web-apps.txt') as web_apps_file:
            self._web_apps = web_apps_file.read().strip().split('\n')

    def append_localized_name(self, locale, name):
        if name != self._default_name:
            self._name_locales.append(locale)
            self._localized_names[locale] = name

    def append_localized_url(self, locale, url):
        if url != self._default_url:
            self._url_locales.append(locale)
            self._localized_urls[locale] = url

    def _get_names(self):
        name_string = self._default_name
        for locale in self._name_locales:
            name_string += '\nName[%s]=%s' % (locale,
                                              self._localized_names[locale])
        return name_string

    def _get_exec(self):
        # If this link is white-listed as a web app,
        # include the appropriate command
        if self.get('Id') in self._web_apps:
            webapp_prefix = 'webapp:' +  self._get_startup_wmclass() + '@'
        else:
            webapp_prefix = ''

        # If there's only one URL for this link,
        # just return an exec which opens that url in the browser.
        if len(self._url_locales) == 0:
            return 'gio open ' + webapp_prefix + self._default_url

        # Otherwise, send each url with its respective locale 
        # to eos-exec-localized.
        exec_str = 'eos-exec-localized '
        exec_str += '\'gio open ' + webapp_prefix + self._default_url + '\' '

        # Process locales in the same order they were appended
        for locale in self._url_locales:
            url = self._localized_urls[locale]
            exec_str += locale + ':\'gio open ' + webapp_prefix + url + '\' '

        return exec_str

    def _get_startup_wmclass(self):
        # If this link is white-listed as a web app,
        # add the window manager class field so that the launched
        # web app uses its own taskbar icon.
        # Note that for localized execs, this only works properly
        # for the default URL -- other locales will have the
        # windows associated with the browser taskbar icon.
        if self.get('Id') in self._web_apps:
            parsed = urllib.parse.urlparse(self._default_url)
            wmclass = parsed.netloc
            trimmed_path = parsed.path.rstrip('/')
            if trimmed_path:
                wmclass += '_'
                wmclass += trimmed_path.replace('/', '_')
            return wmclass
        else:
            return None

    def get(self, key):
        if key == 'Name':
            return self._get_names()
        elif key == 'Exec':
            return self._get_exec()
        elif key == 'StartupWMClass':
            return self._get_startup_wmclass()
        elif key == 'X-Endless-LaunchMaximized':
            return 'true'
        elif key in ['TryExec',
                     'X-Endless-SplashBackground']:
            return None
        else:
            return super(LinkObject, self).get(key)

    def get_desktop_dir(self):
        return self._desktop_dir

class AppObject(DesktopObject):

    json_keys = {
        'Name': 'title',
        'Id': 'application-id',
        'Core': 'core',
        'Personalities': 'personalities',
        'Comment': 'subtitle',
        'Categories': 'category',
        'Exec': 'exec',
        'TryExec': 'tryexec',
        'Icon': 'application-id',
        'Folder': 'folder',
        'Index': 'desktop-position',
        'X-Endless-LaunchMaximized': 'splash-screen-type',
        'X-Endless-SplashBackground': 'custom-splash-screen'
    }

    def __init__(self, data, bundle_desktop_dir):
        super(AppObject, self).__init__(data)
        self._bundle_desktop_dir = bundle_desktop_dir
        self._prefix = ''
        self._icon_prefix = 'eos-app-'

    def get_desktop_dir(self):
        return self._bundle_desktop_dir

class FolderObject(DesktopObject):

    json_keys = {
        'Id': 'folderId',
        'Name': 'folderName'
    }

    def __init__(self, data, desktop_dir):
        super(FolderObject, self).__init__(data)
        self._desktop_dir = desktop_dir
        self._prefix = 'eos-folder-'
        self._suffix = '.directory.in'
        self.defaults['Type'] = 'Directory'

    def get(self, key):
        if key in ['Comment',
                   'Exec',
                   'TryExec',
                   'Icon',
                   'Categories',
                   'X-Endless-LaunchMaximized',
                   'X-Endless-SplashBackground']:
            return None
        else:
            return super(FolderObject, self).get(key)

    def get_desktop_dir(self):
        return self._desktop_dir
