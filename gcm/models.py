import vte


class Host:
    def __init__(self, *args):
        try:
            self.i = 0
            self.group = self.get_arg(args, None)
            self.name = self.get_arg(args, None)
            self.description = self.get_arg(args, None)
            self.host = self.get_arg(args, None)
            self.user = self.get_arg(args, None)
            self.password = self.get_arg(args, None)
            self.private_key = self.get_arg(args, None)
            self.port = self.get_arg(args, 22)
            self.tunnel = self.get_arg(args, '').split(",")
            self.type = self.get_arg(args, 'ssh')
            self.commands = self.get_arg(args, None)
            self.keep_alive = self.get_arg(args, 0)
            self.font_color = self.get_arg(args, '')
            self.back_color = self.get_arg(args, '')
            self.x11 = self.get_arg(args, False)
            self.agent = self.get_arg(args, False)
            self.compression = self.get_arg(args, False)
            self.compressionLevel = self.get_arg(args, '')
            self.extra_params = self.get_arg(args, '')
            self.log = self.get_arg(args, False)
            self.backspace_key = self.get_arg(args, int(vte.ERASE_AUTO))
            self.delete_key = self.get_arg(args, int(vte.ERASE_AUTO))
        except KeyError:
            pass

    def get_arg(self, args, default):
        arg = args[self.i] if len(args) > self.i else default
        self.i += 1
        return arg

    def __repr__(self):
        return "group=[%s],\t name=[%s],\t host=[%s],\t type=[%s]" % (
            self.group, self.name, self.host, self.type
        )

    def tunnel_as_string(self):
        return ",".join(self.tunnel)

    def clone(self):
        return Host(self.group, self.name, self.description,
                    self.host, self.user, self.password, self.private_key,
                    self.port, self.tunnel_as_string(), self.type,
                    self.commands, self.keep_alive, self.font_color,
                    self.back_color, self.x11, self.agent, self.compression,
                    self.compressionLevel, self.extra_params,
                    self.log, self.backspace_key, self.delete_key)
