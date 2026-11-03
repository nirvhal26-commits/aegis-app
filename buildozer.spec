[app]
title = AEGIS
package.name = aegis
package.domain = org.shreyash
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,mp3,json
version = 1.0
requirements = python3,kivy==2.2.1,kivymd==1.1.1,pillow,plyer,pyjnius,android
icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/presplash.png
presplash.color = #121726
orientation = portrait
fullscreen = 0

android.permissions = SEND_SMS,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,CAMERA,VIBRATE,WAKE_LOCK
android.api = 33
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
