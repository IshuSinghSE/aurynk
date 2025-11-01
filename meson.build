# Meson build file for Mirage
project('mirage',
  version: '0.1.0',
  meson_version: '>= 0.59.0',
  license: 'GPL-3.0-or-later',
)

# Python installation
python = import('python')
py_installation = python.find_installation('python3')

# Check Python version
if not py_installation.language_version().version_compare('>= 3.11')
  error('Python 3.11 or newer is required')
endif

# Application ID
application_id = 'com.yourdomain.mirage'

# Prefix and directories
prefix = get_option('prefix')
bindir = prefix / get_option('bindir')
datadir = prefix / get_option('datadir')
pkgdatadir = datadir / meson.project_name()

# Build subdirectories
subdir('data')

# Generate Python constants file (if needed in future)
conf = configuration_data()
conf.set('VERSION', meson.project_version())
conf.set('APP_ID', application_id)
conf.set('PKGDATADIR', pkgdatadir)
conf.set('PYTHON', py_installation.full_path())

# Summary
summary({
  'prefix': prefix,
  'bindir': bindir,
  'datadir': datadir,
}, section: 'Directories')

summary({
  'Python': py_installation.full_path(),
  'Python version': py_installation.language_version(),
}, section: 'Build environment')
