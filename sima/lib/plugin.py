# -*- coding: utf-8 -*-

class Plugin():
    """
    First non-empty line of the docstring is used as description
    Rest of the docstring at your convenience.

    The plugin Name MUST be the same as the module (file name), case
    insensitive: for instance plugin.py → Plugin
    It eases plugins discovery and simplifies the code to handle them,
    IMHO, it's a fair trade-off.
    """

    @classmethod
    def info(cls):
        """self documenting class method
        """
        return {'name': cls.__name__,
                'doc': cls.__doc__.strip(' \n').splitlines()[0]
                }

    def __init__(self, daemon):
        self.log = daemon.log
        self.__daemon = daemon
        self.plugin_conf = None
        self.__get_config()

    def __str__(self):
        return self.__class__.__name__

    def __get_config(self):
        """Get plugin's specific configuration from global applications's config
        """
        conf = self.__daemon.config
        for sec in conf.sections():
            if sec.lower() == self.__class__.__name__.lower():
                self.plugin_conf = dict(conf.items(sec))
        if self.plugin_conf:
            self.log.debug('Got config for {0}: {1}'.format(self,
                                                            self.plugin_conf))

    def callback_player(self):
        """
        Called on player changes
        """
        pass

    def callback_playlist(self):
        """
        Called on playlist changes

        Not returning data
        """
        pass

    def callback_next_song(self):
        """Not returning data,
        Could be use to scrobble, maintain an history…
        """
        pass

    def callback_need_song(self):
        """Returns a list of Track objects to add
        """
        pass

    def shutdown(self):
        pass


# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab
