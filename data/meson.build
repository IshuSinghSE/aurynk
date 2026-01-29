# Data directory build file

# Install icon

icon_sizes = ['16x16', '24x24', '32x32', '48x48', '64x64', '128x128', '256x256', '512x512']
icon_names = [
  'io.github.IshuSinghSE.aurynk.png',
  'io.github.IshuSinghSE.aurynk.device.png',
  'io.github.IshuSinghSE.aurynk.monitor.png',
  'io.github.IshuSinghSE.aurynk.add-device.png',
  'io.github.IshuSinghSE.aurynk.mirror.png'
]


foreach size : icon_sizes
  foreach name : icon_names
    install_data(
      'icons/hicolor/' + size + '/apps/' + name,
      install_dir: datadir / 'icons' / 'hicolor' / size / 'apps'
    )
  endforeach
endforeach

# Install SVG icon if present
install_data(
  'icons/hicolor/scalable/apps/io.github.IshuSinghSE.aurynk.svg',
  install_dir: datadir / 'icons' / 'hicolor' / 'scalable' / 'apps'
)

# Install tray icon variants (SVG in data/icons/)
tray_variants = [
  'io.github.IshuSinghSE.aurynk.tray.svg',
  'io.github.IshuSinghSE.aurynk.tray-black.svg',
  'io.github.IshuSinghSE.aurynk.tray-white.svg',
  'io.github.IshuSinghSE.aurynk.tray-filled.svg'
]

foreach variant : tray_variants
  install_data(
    'icons/' + variant,
    install_dir: pkgdatadir / 'icons'
  )
endforeach

# Compile GResource
gnome = import('gnome')
gresource = gnome.compile_resources(
  'io.github.IshuSinghSE.aurynk',
  'io.github.IshuSinghSE.aurynk.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

# Install desktop file
i18n = import('i18n')
desktop_file = i18n.merge_file(
  input: 'io.github.IshuSinghSE.aurynk.desktop.in',
  output: 'io.github.IshuSinghSE.aurynk.desktop',
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
  input: 'io.github.IshuSinghSE.aurynk.metainfo.xml',
  output: 'io.github.IshuSinghSE.aurynk.metainfo.xml',
  po_dir: '../po',  # If you add translations
  install: true,
  install_dir: datadir / 'metainfo'
)

# Validate appdata file
appstream_util = find_program('appstream-util', required: false)
if appstream_util.found()
  test('Validate appdata file', appstream_util, args: ['validate', appdata_file])
endif
