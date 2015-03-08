import unix

# Extra arguments for 'scp' command as integer argument name raise syntax error
# when there are passed directly but not in kwargs.
_SCP_EXTRA_ARGS = {'force_protocol1': '1',
                   'force_protocol2': '2',
                   'force_localhost': '3',
                   'force_ipv4': '4',
                   'force_ipv6': '6'}

# Set some default value for SSH options of 'scp' command.
_SCP_DEFAULT_OPTS = {'StrictHostKeyChecking': 'no', 'ConnectTimeout': '2'}


class Remote(object):
    def __init__(self, host):
        self._host = host


    def _format_ssh_arg(self, user, host, filepath):
        return (('%s@' % user if (user and host) else '')
                + (host or '')
                + (('%s%s' % (':' if host else '', filepath))
                   if filepath
                   else ''))


    def scp(self, src_file, dst_file, **kwargs):
        # ssh_options (-o) can be passed many time so this must be a list.
        kwargs['o'] = kwargs.get('o', [])
        if type(kwargs['o']) not in (list, tuple):
            raise AttributeError("'o' argument of 'scp' function must be a list"
                                 " as there can be many SSH options passed to "
                                 "the command.")

        # Python don't like when argument name is an integer but passing them
        # with kwargs seems to work. So use extra arguments for interger options
        # of the scp command.
        for mapping, opt in _SCP_EXTRA_ARGS.items():
            if kwargs.pop(mapping, False):
                kwargs.setdefault(opt, True)

        # Change default value of some SSH options (like host key checking and
        # connect timeout).
        cur_opts = [opt.split('=')[0] for opt in kwargs['o']]
        kwargs['o'].extend('%s=%s' % (opt, default)
                           for opt, default in _SCP_DEFAULT_OPTS.items()
                           if opt not in cur_opts)

        # Format source and destination arguments.
        src = self._format_ssh_arg(kwargs.pop('src_user', ''),
                                   kwargs.pop('src_host', ''),
                                   src_file)
        dst = self._format_ssh_arg(kwargs.pop('dst_user', ''),
                                   kwargs.pop('dst_host', ''),
                                   dst_file)

        return self._host.execute('scp', src, dst, **kwargs)


    def rsync(self, src_file, dst_file, **kwargs):
        src = self._format_ssh_arg(kwargs.pop('src_user', ''),
                                   kwargs.pop('src_host', ''),
                                   src_file)
        dst = self._format_ssh_arg(kwargs.pop('dst_user', ''),
                                   kwargs.pop('dst_host', ''),
                                   dst_file)

        return self._host.execute('rsync', src, dst, **kwargs)


    def tar(self, src_file, dst_file, src_opts={}, dst_opts={}, **kwargs):
        src_ssh = '%s' % self._format_ssh_arg(kwargs.pop('src_user', ''),
                                              kwargs.pop('src_host', ''),
                                              '')
        dst_ssh = '%s' % self._format_ssh_arg(kwargs.pop('dst_user', ''),
                                              kwargs.pop('dst_host', ''),
                                              '')

        interactive = kwargs.pop('interactive', False)

        src_cmd = ['tar cf -']
        src_opts.update(kwargs)
        src_opts.setdefault('C', os.path.dirname(src_file))
        self._format_command(src_cmd, [os.path.basename(src_file)], src_opts)

        dst_cmd = ['tar xf -']
        dst_opts.update(kwargs)
        dst_opts.setdefault('C', dst_file)
        self._format_command(dst_cmd, [], dst_opts)

        cmd = ['ssh %s' % src_ssh if src_ssh else '']
        cmd.extend(src_cmd)
        cmd.append('|')
        cmd.append('ssh %s' % dst_ssh if dst_ssh else '')
        cmd.extend(dst_cmd)
        return self._host.execute(*cmd, interactive=interactive)


    def get(self, rmthost, rmtpath, localpath, **kwargs):
        if unix.ishost(self._host, 'Remote') and rmthost == 'localhost':
            return unix.Local().remote.put(rmtpath,
                                           self._host.ip,
                                           localpath,
                                           rmtuser=kwargs.pop('rmtuser',
                                                              self._host.username),
                                           **kwargs)

        method = kwargs.pop('method', 'scp')
        rmtuser = kwargs.pop('rmtuser', 'root')

        try:
            args = (rmtpath, localpath)
            kwargs.update(src_host=rmthost, src_user=rmtuser)
            return getattr(self, method)(*args, **kwargs)
        except AttributeError:
            return [False, [], ["unknown copy method '%s'" % method]]


    def put(self, localpath, rmthost, rmtpath, **kwargs):
        if unix.ishost(self._host, 'Remote') and rmthost == 'localhost':
            return unix.Local().remote.get(self._host.ip,
                                           localpath,
                                           rmtpath,
                                           rmtuser=kwargs.pop('rmtuser',
                                                              self._host.username),
                                           **kwargs)

        method = kwargs.pop('method', 'scp')
        rmtuser = kwargs.pop('rmtuser', 'root')

        try:
            args = (localpath, rmtpath)
            kwargs.update(dst_host=rmthost, dst_user=rmtuser)
            return getattr(self, method)(*args, **kwargs)
        except AttributeError:
            return [False, [], ["unknown copy method '%s'" % method]]
