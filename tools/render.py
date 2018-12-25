#!/usr/bin/env python
# TODO: opengraph: http://ogp.me/
# TODO: inclusion de markdown, asciidoc, restructured
# TODO: integration avec mercurial/git/svn ?
# TODO: config file: ini with sections for site parts and default name
#       sections are used as optional positional arg. ala Makefile
#       -c / --config to overload the default one

import sys
from os import listdir, makedirs
from os.path import basename, dirname, splitext, join, isdir
from glob import iglob
import argparse
import datetime
from itertools import izip
import mimetypes
from urlparse import urljoin

import jinja2
import yaml
import markdown

import locale
mimetypes.init()


def error(msg, args=None, with_help=None):
    """ Print an error message and exit the program """
    if args is None:
        args = []
    sys.stderr.write('ERROR: ' + msg % args + '\n\n')
    if with_help:
        with_help.print_help()
    sys.exit(1)


def info(msg, *args):
    """ Print a debug message """
    if __debug__:
        sys.stderr.write('INFO: ' + msg % args + '\n')


class Config(dict):
    """ Class to hold config params, from command line and config file """
    def __repr__(self):
        return 'Config(%s)' % dict.__repr__(self)

    def __getattr__(self, name):
        val = self.get(name)
        if isinstance(val, dict):
            return self.__class__(val)
        if isinstance(val, list):
            return tuple(val)
        return val

    def __setattr__(self, name, value):
        raise TypeError("'Config' is immutable")

    def __setitem__(self, name, value):
        raise TypeError("'Config' is immutable")


class ConfigLoader(object):
    """ Class to load configurations, from command line and config. file """
    def __init__(self):
        self.argparser = None
        self._init_argparser()

    def _init_argparser(self):
        """ Initialize the ArgumentParser """
        self.argparser = argparse.ArgumentParser(
            description="Website renderer"
        )
        self.argparser.add_argument(
            '-o', '--output',
            metavar='FILE',
            type=argparse.FileType('wb'),
            default=sys.stdout,
            help="output file"
        )
        self.argparser.add_argument(
            '--output-dir',
            dest='output_dir',
            metavar='DIRECTORY',
            help="output files to DIRECTORY"
        )
        # self.argparser.add_argument(
        #     '-r', '--recurse',
        #     help='recurse in sub-directories',
        #     action='store_true',
        #     default=False
        # )
        self.argparser.add_argument(
            '-d', '--data',
            metavar='FILE',
            help="read yaml data from FILE in filename based scope",
            action='append',
            default=[]
        )
        self.argparser.add_argument(
            '--data-dir',
            metavar='DIRECTORY',
            dest='data_dir',
            help='read all datafiles in DIRECTORY'
        )
        self.argparser.add_argument(
            '-t', '--template',
            help='use TEMPLATE file or name to format data',
        )
        self.argparser.add_argument(
            '--templates-dir',
            metavar='DIRECTORY',
            action='append',
            dest='templates_dir',
            default=[],
            help='directory where to search for templates'
        )
        self.argparser.add_argument(
            '-a', '--all',
            dest='render_all',
            action='store_true',
            default=False,
            help=("render all templates in template-dir"
                  "that are not just macro (*.jinja)")
        )
        self.argparser.add_argument(
            '-g', '--global',
            action='append',
            dest='global_data',
            default=[],
            metavar='FILE',
            help='like -t but in global scope'
        )
        self.argparser.add_argument(
            '-c', '--config',
            type=argparse.FileType('rb'),
            metavar='FILE',
            help="use a config file"
        )

        self.argparser.add_argument(
            '-l', '--lang',
            default='',
            metavar='LANG',
            help='locale to use (also define the global "lang" var)'
        )

        self.argparser.add_argument(
            '-b', '--base',
            default='',
            metavar='URI',
            help='define the base URI for links'
        )

        # TODO: -D --define a=b

    def load(self):
        """ Load all configurations """
        return self.argparser.parse_args()


class Command(object):
    """ Main program """
    def __init__(self):
        self.config = None
        self.data = None
        self.templates = None

    def _init_config(self, loader):
        """ initialize the configuration """
        self.config = loader.load()
        # TODO: param de conf ou locale
        self.config.encoding = 'utf-8'

    def _load_data(self):
        """ Load yaml data """
        self.data = DataLoader()
        self.data.load(self.config.data,
                       self.config.data_dir,
                       self.config.global_data)
        self.data.globals.update({
            'today': datetime.date.today(),
            'now': datetime.datetime.utcnow().replace(microsecond=0),
            'encoding': self.config.encoding,
            'lang': self.config.lang,
            'mediatypes': {
                k[1:]: v for k, v
                in (mimetypes.types_map.items() +
                    mimetypes.common_types.items())
            }
        })

    def _load_templates(self):
        """ Load templates to render """
        # TODO: extensions and create_dir as a param
        self.templates = TemplateLoader(self.config, ['html'], True)
        self.templates.load(self.data.globals,
                            self.config.template,
                            self.config.render_all)

    def render(self):
        """ Render all templates and save the outputs """
        locale.setlocale(locale.LC_ALL, self.config.lang)
        for out, template in self.templates:
            out.write(
                template.render(
                    self.data.locals
                ).encode(self.config.encoding)
            )
            out.close()

    def main(self):
        """ main command line program """
        try:
            self._init_config(ConfigLoader())
            self._load_data()
            self._load_templates()
            self.render()
        except jinja2.exceptions.TemplateNotFound, ex:
            if not ex.name:
                error("Can't find template to render."
                      "You must specify -a and --templates-dir or -t")
            else:
                error("Can't find template '%s'.", [ex.name])
        except TemplateOutputError:
            error("You must specify a --output-dir when rendering several"
                  "templates at once.")


class DataLoader(object):
    """ Class responsible to load all YAML data (global and local) """
    def __init__(self, recurse=False):
        self.recurse = recurse
        self.globals = {}
        self.locals = {}

    def _load_file_with_scope(self, filename):
        """ Load a YAML file with the scope of its filename """
        info("loading '%s'", filename)
        scope = splitext(basename(filename))[0]
        data = _parse_dates(yaml.load(file(filename, 'rb')))
        return (scope, data)

    def load_local(self, filename):
        """ Load a local data file """
        self.locals.update(dict([self._load_file_with_scope(filename)]))

    def load_globals(self, filename):
        """ Load a global data file """
        self.globals.update(self._load_file_with_scope(filename)[1])

    def load_dir(self, dir_name):
        """ Load a directory of data files """
        for filename in iglob(join(dir_name, '*.yml')):
            self.load_local(filename)
        # FIXME
        if self.recurse:
            for subdir in listdir(dir_name):
                subdir = join(dir_name, subdir)
                if isdir(subdir):
                    self.locals.update({
                        basename(subdir): self.load_dir(subdir)
                    })

    def load(self, datafiles, datadir, global_datafiles):
        """ Load data """
        for filename in global_datafiles:
            self.load_globals(filename)
        for filename in datafiles:
            self.load_local(filename)
        if datadir:
            self.load_dir(datadir)


def _parse_dates(data):
    """ try to convert string values to dates """
    if isinstance(data, dict):
        return {k: _parse_dates(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_parse_dates(v) for v in data]
    if isinstance(data, str):
        return _date_or_string(data)
    else:
        return data


class TemplateOutputError(Exception):
    """
    Exception raised when the renderer don't know where to save its output
    """
    pass


def mkd_formater(base="/"):
    """ format a markdown value
    exts:
    https://github.com/favalex/python-asciimathml
    https://github.com/aleray/mdx_cite
    https://github.com/aleray/mdx_semanticwikilinks
    https://github.com/aleray/mdx_semanticdata
    https://bitbucket.org/jeunice/mdx_smartypants
    https://github.com/aleray/mdx_outline
    http://code.google.com/p/markdown-typografix/
    """
    # TODO: read options from an ini file
    mkd = markdown.Markdown(
        extensions=[
            'abbr',
            'attr_list',
            'def_list',
            'fenced_code',
            'codehilite',
            'tables',
            'smart_strong',
            'admonition',
            'headerid',
            'meta',
            'sane_lists',
            'toc',
            # 'wikilink'
        ],
        extension_config={
            'codehilite': [('guess_lang', True), ('linenums', False)],
            'headerid': [('level', 3), ('forceid', True)],
            'wikilink': [('base_url', base), ('end_url', '')]
        },
        output_format='xhtml5',
        smart_emphasis=True,
        lazy_ol=True,
        enable_attributes=True
    )
    return lambda v: mkd.convert(v)


def date_formater(val, fmt_date=None, fmt_time=None):
    """ template filter: format a date (can be a date or a string)"""
    if val is None:
        return "None"
    if isinstance(val, datetime.datetime):
        fmt = fmt_time or fmt_date
    elif isinstance(val, datetime.date):
        fmt = fmt_date
    else:
        raise ValueError(repr(val))
    if not fmt:
        return unicode(val)
    fmt = fmt.replace('%o', '%d' + en_enum(val.day))
    return unicode(val.strftime(fmt.encode('utf-8')), 'utf-8')


def _to_date(d):
    if isinstance(d, datetime.datetime):
        return d.date()
    return d


def date_comparator(val, inf, sup):
    """ test if a date is between two others """
    dates = [val, inf, sup]
    if any(map(lambda d: isinstance(d, datetime.date), dates)):
        dates = map(_to_date, dates)
    val, inf, sup = dates
    return inf <= val <= sup


def _date_or_string(value):
    """ try to parse a string, returns the string if fails """
    try:
        return datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M')
    except:
        return value


def url_builder(base):
    """ build a URL by appending a base (template filter) """
    return lambda v: urljoin(base, v)


def en_enum(num):
    """ get the string representing an enumerated number """
    return {1: 'st', 2: 'nd', 3: 'rd'}.get(num, 'th')


def _get_date(date):
    if isinstance(date, datetime.datetime):
        return date.date()
    if isinstance(date, datetime.date):
        return date
    raise ValueError


def group_events(events, cat=None):
    groups = {}
    for event in events:
        if cat is not None and cat not in event["cat"]:
            continue
        d = _get_date(event["start"])
        if d not in groups:
            groups[d] = []
        groups[d].append(event)
    for events in groups.values():
        events.sort(key=lambda e: e['start'])
    return sorted(groups.items())


def expand_events(events, keynotes, papers, pages):
    for event in events:
        if "keynote" in event:
            k = keynotes[event["keynote"]]
            event["title"] = "Keynote {} {}".format(k['gname'], k['fname'])
            event["desc"] = k["title"]
            event["id"] = event["keynote"]
            event["link"] = pages["keynotes"] + "#" + event["keynote"]
        if "session" in event:
            if event["title"]:
                event["title"] = u"Session {} \u2013 {}".format(event["session"],
                                                                event["title"])
            else:
                event["title"] = u"Session {}".format(event["session"])

            event["desc"] = True
            event["papers"] = sorted([
                p for p in papers if p["session"] == event["session"]
            ], key=lambda p: p.get("number", 0))
    return events

def prev_page(sequence, pages, current):
    idx = 0
    if current in sequence:
        idx = max(idx, sequence.index(current) - 1)
    return pages[sequence[idx]]

def next_page(sequence, pages, current):
    idx = len(sequence) - 1
    if current in sequence:
        idx = min(idx, sequence.index(current) + 1)
    return pages[sequence[idx]]

FILTERS = {
    'date': date_formater,
    'groupevents': group_events,
    'next_day': lambda v: v + datetime.timedelta(1) if v is not None else None,
    'expand_events': expand_events,
    'prev_page': prev_page,
    'next_page': next_page
}


def _future_date(d):
    if isinstance(d, datetime.datetime):
        return d.date() >= datetime.date.today()
    if isinstance(d, datetime.date):
        return d >= datetime.date.today()
    return False

TESTS = {
    'future_date': _future_date,
    'same_month': lambda d, o: (d.year == o.year) and (d.month == o.month),
    'same_day': lambda d, o: ((d.year == o.year) and
                              (d.month == o.month) and
                              (d.day == o.day))
}


class TemplateLoader(object):
    """ Init the jinja env and load templates """
    def __init__(self, config, extensions, create_dirs=False):
        self.create_dirs = create_dirs
        self.templates_dir = config.templates_dir
        self.output_dir = config.output_dir
        self.output = config.output
        self.extensions = extensions
        self.base = config.base
        self._env = None
        self.templates = []
        self.outputs = []

    def load(self, global_data=None, template=None, load_all=False):
        """ Load templates and init the outputs """
        self._init_env(template)
        self.templates = self.get_templates(template, global_data)
        self.outputs = self.get_outputs()

    def __iter__(self):
        return izip(self.outputs, self.templates)

    def _init_env(self, template):
        """ Initialize the jinja2 Environment """
        if self.templates_dir:
            self._env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(self.templates_dir))
        elif template:
            self._env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(dirname(template)))
        else:
            raise jinja2.exceptions.TemplateNotFound('')
        self._env.filters.update(FILTERS)
        self._env.filters['url'] = url_builder(self.base)
        self._env.filters['mkd'] = mkd_formater(self.base)
        self._env.tests.update(TESTS)

    def get_templates(self, template, global_data):
        """ Return the required template(s) """
        if self.templates_dir:
            if template:
                template_names = [template]
            # elif self.render_all:
            #     template_names = self._env.list_templates(
            #         extensions=self.extensions)
        if template:
            template_names = [basename(template)]
        return [self._env.get_template(t, globals=global_data)
                for t in template_names]

    def get_outputs(self):
        """
        Return a list of file object where to write the template rendering.
        if `create_dir` is True, create the destination directory if needed,
        otherwise, an IOError may be raised.
        """
        if len(self.templates) == 1:
            return [self.output]
        if not self.output_dir:
            raise TemplateOutputError
        filenames = [join(self.output_dir, t.name) for t in self.templates]
        if self.create_dirs:
            for filedir in map(dirname, filenames):
                if not isdir(filedir):
                    makedirs(filedir)
        return [file(f, 'wb') for f in filenames]


if __name__ == '__main__':
    Command().main()
