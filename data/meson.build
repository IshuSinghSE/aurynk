# Data directory build file

# Install icon
install_data(
  'icons' / 'com.yourdomain.aurynk.png',
  install_dir: datadir / 'icons' / 'hicolor' / 'scalable' / 'apps'
)

# If you have an SVG icon, also install it
# install_data(
#   'icons' / 'com.yourdomain.aurynk.svg',
#   install_dir: datadir / 'icons' / 'hicolor' / 'scalable' / 'apps'
# )

# Compile GResource
gnome = import('gnome')
gresource = gnome.compile_resources(
  'com.yourdomain.aurynk',
  'com.yourdomain.aurynk.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

# Install desktop file
i18n = import('i18n')
desktop_file = i18n.merge_file(
  input: 'com.yourdomain.aurynk.desktop.in',
  output: 'com.yourdomain.aurynk.desktop',
  type: 'desktop',
  po_dir: '../po',  # If you add translations
  install: true,
  install_dir: datadir / 'applications'
)

# Validate desktop file
desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils, args: [desktop_file])
endif

# Install appdata file
appdata_file = i18n.merge_file(
  input: 'com.yourdomain.aurynk.appdata.xml',
  output: 'com.yourdomain.aurynk.appdata.xml',
  po_dir: '../po',  # If you add translations
  install: true,
  install_dir: datadir / 'metainfo'
)

# Validate appdata file
appstream_util = find_program('appstream-util', required: false)
if appstream_util.found()
  test('Validate appdata file', appstream_util, args: ['validate', appdata_file])
endif
