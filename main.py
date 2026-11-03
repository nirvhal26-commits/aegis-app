import hashlib
import hmac
import math
import os
import time
import webbrowser
from datetime import datetime

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import BooleanProperty, StringProperty
from kivy.storage.jsonstore import JsonStore
from kivy.uix.screenmanager import FadeTransition, ScreenManager
from kivy.utils import platform
from kivymd.app import MDApp
from kivymd.toast import toast
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.pickers import MDDatePicker
from kivymd.uix.screen import MDScreen

IS_ANDROID = platform == "android"

try:
    from plyer import accelerometer, battery, flashlight, gps
    has_sensor = True
except ImportError:
    has_sensor = False

if IS_ANDROID:
    from android.permissions import Permission, request_permissions
    from jnius import autoclass
else:
    # Desktop preview size only; on a phone the app fills the screen.
    Window.size = (414, 736)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SIREN_PATH = os.path.join(BASE_DIR, "siren.mp3")

FALL_THRESHOLD = 25.0      # m/s^2 total acceleration (about 2.5 g)
SENSOR_INTERVAL = 0.05     # seconds between accelerometer checks
COOLDOWN_SECONDS = 30      # pause detection after an alert/cancel


KV = '''
#:import FadeTransition kivy.uix.screenmanager.FadeTransition

ScreenManager:
    transition: FadeTransition()
    SplashScreen:
    SignUpScreen:
    SignInScreen:
    MainScreen:
    ProfileScreen:

<SplashScreen>:
    name: 'splash'
    md_bg_color: 0.07, 0.09, 0.15, 1 
        
    MDFloatLayout:
        MDLabel:
            id: logo_label
            text: "AEGIS"
            halign: "center"
            pos_hint: {"center_x": .5, "center_y": .6}
            font_style: "H2"
            theme_text_color: "Custom"
            text_color: 0, 0.8, 1, 1  
            bold: True
            opacity: 0  
            
        MDLabel:
            id: dev_label
            text: "Developed by SHREYASH JABARE"
            halign: "center"
            pos_hint: {"center_x": .5, "center_y": .15}
            font_style: "Caption"
            theme_text_color: "Custom"
            text_color: 0.6, 0.6, 0.6, 1
            opacity: 0  

<SignUpScreen>:
    name: 'signup'
    md_bg_color: 0.07, 0.09, 0.15, 1
        
    MDBoxLayout:
        orientation: 'vertical'
        padding: "30dp"
        spacing: "15dp"
        pos_hint: {"center_x": .5, "center_y": .5}
        size_hint_y: None
        height: self.minimum_height

        MDLabel:
            text: "Create Account"
            halign: "center"
            font_style: "H4"
            theme_text_color: "Custom"
            text_color: app.theme_cls.primary_color
            bold: True

        MDTextField:
            id: name_input
            hint_text: "Full Name"
            mode: "rectangle"
            icon_right: "account"

        MDTextField:
            id: mobile_input
            hint_text: "Mobile Number"
            mode: "rectangle"
            icon_right: "phone"
            input_filter: "int"
            max_text_length: 10

        MDBoxLayout:
            size_hint_y: None
            height: self.minimum_height
            spacing: "10dp"
            
            MDTextField:
                id: dob_input
                hint_text: "Birth Date (YYYY-MM-DD)"
                mode: "rectangle"
                on_focus: if not self.focus: app.calculate_age(self.text)
                
            MDIconButton:
                icon: "calendar"
                pos_hint: {"center_y": .5}
                theme_text_color: "Custom"
                text_color: app.theme_cls.primary_color
                md_bg_color: 0.2, 0.2, 0.2, 1
                on_release: app.show_date_picker()

        MDTextField:
            id: age_input
            hint_text: "Age (Auto Calculated)"
            mode: "rectangle"
            readonly: True

        MDBoxLayout:
            size_hint_y: None
            height: self.minimum_height
            spacing: "10dp"
            
            MDTextField:
                id: password_input
                hint_text: "Create Password"
                mode: "rectangle"
                password: True
                helper_text: "Min 8 chars, num+letters"
                helper_text_mode: "on_error"
                
            MDIconButton:
                icon: "eye-off"
                pos_hint: {"center_y": .5}
                theme_text_color: "Custom"
                text_color: app.theme_cls.primary_color
                on_release:
                    password_input.password = not password_input.password
                    self.icon = "eye" if not password_input.password else "eye-off"

        MDFillRoundFlatButton:
            text: "Send OTP & Register"
            pos_hint: {"center_x": .5}
            size_hint_x: 1
            on_release: app.verify_signup()

        MDTextButton:
            text: "Already have an account? Log In"
            pos_hint: {"center_x": .5}
            theme_text_color: "Hint"
            on_release: app.root.current = 'signin'

<SignInScreen>:
    name: 'signin'
    md_bg_color: 0.07, 0.09, 0.15, 1
        
    MDBoxLayout:
        orientation: 'vertical'
        padding: "30dp"
        spacing: "20dp"
        pos_hint: {"center_x": .5, "center_y": .5}
        size_hint_y: None
        height: self.minimum_height

        MDLabel:
            text: "Welcome Back!"
            halign: "center"
            font_style: "H4" 
            theme_text_color: "Custom"
            text_color: app.theme_cls.primary_color
            bold: True

        MDTextField:
            id: login_mobile
            hint_text: "Mobile Number"
            mode: "rectangle"
            icon_right: "phone"
            input_filter: "int"
            max_text_length: 10

        MDBoxLayout:
            size_hint_y: None
            height: self.minimum_height
            spacing: "10dp"
            
            MDTextField:
                id: login_password
                hint_text: "Password"
                mode: "rectangle"
                password: True
                
            MDIconButton:
                icon: "eye-off"
                pos_hint: {"center_y": .5}
                theme_text_color: "Custom"
                text_color: app.theme_cls.primary_color
                on_release:
                    login_password.password = not login_password.password
                    self.icon = "eye" if not login_password.password else "eye-off"

        MDFillRoundFlatButton:
            text: "Log In"
            pos_hint: {"center_x": .5}
            size_hint_x: 1
            on_release: app.verify_login()

<MainScreen>:
    name: 'main'
    md_bg_color: 0.07, 0.09, 0.15, 1

    MDBoxLayout:
        orientation: 'vertical'
        
        MDTopAppBar:
            title: "AEGIS"
            elevation: 2
            md_bg_color: 0.04, 0.06, 0.1, 1 
            specific_text_color: app.theme_cls.primary_color
            right_action_items: [["account-circle", lambda x: app.open_profile()]]

        MDScrollView:
            MDBoxLayout:
                id: main_layout
                orientation: 'vertical'
                padding: "20dp"
                spacing: "20dp"
                size_hint_y: None
                height: self.minimum_height

                MDBoxLayout:
                    id: contacts_box
                    orientation: 'vertical'
                    spacing: "15dp"
                    size_hint_y: None
                    height: self.minimum_height

                    MDLabel:
                        text: "Add Emergency Contacts"
                        halign: "center"
                        font_style: "Subtitle1"
                        theme_text_color: "Custom"
                        text_color: app.theme_cls.primary_color
                        bold: True

                    MDTextField:
                        id: main_contact_1
                        hint_text: "Mobile 1 (Family)"
                        mode: "rectangle"
                        input_filter: "int"
                        max_text_length: 10

                    MDTextField:
                        id: main_contact_2
                        hint_text: "Mobile 2 (Family)"
                        mode: "rectangle"
                        input_filter: "int"
                        max_text_length: 10

                    MDTextField:
                        id: main_contact_3
                        hint_text: "Mobile 3 (Family)"
                        mode: "rectangle"
                        input_filter: "int"
                        max_text_length: 10

                    MDFillRoundFlatButton:
                        text: "Save Numbers"
                        pos_hint: {"center_x": .5}
                        size_hint_x: 0.8
                        md_bg_color: app.theme_cls.primary_color
                        on_release: app.save_contacts_main()

                Widget:
                    size_hint_y: None
                    height: "10dp"

                MDLabel:
                    text: "Status: Sensor Active"
                    halign: "center"
                    font_style: "H6"
                    bold: True
                    theme_text_color: "Custom"
                    text_color: 0, 1, 0, 1 

                MDFillRoundFlatButton:
                    text: "Find Nearby Hospital"
                    pos_hint: {"center_x": .5}
                    size_hint_x: 0.9
                    md_bg_color: 0, 0.6, 0.6, 1 
                    on_release: app.find_hospital()
                    
                MDFillRoundFlatButton:
                    text: "EMERGENCY SOS"
                    pos_hint: {"center_x": .5}
                    size_hint_x: 0.9
                    md_bg_color: 1, 0, 0, 1
                    on_release: app.call_108()
                    
                Widget:
                    size_hint_y: None
                    height: "20dp"

<ProfileScreen>:
    name: 'profile'
    md_bg_color: 0.07, 0.09, 0.15, 1 
        
    MDBoxLayout:
        orientation: 'vertical'
        
        MDTopAppBar:
            title: "My Profile"
            elevation: 2
            md_bg_color: 0.04, 0.06, 0.1, 1 
            specific_text_color: app.theme_cls.primary_color
            left_action_items: [["arrow-left", lambda x: app.go_back_to_main()]]

        MDScrollView:
            MDBoxLayout:
                orientation: 'vertical'
                padding: "20dp"
                spacing: "15dp"
                size_hint_y: None
                height: self.minimum_height
                
                MDLabel:
                    text: "Name: " + app.user_name
                    theme_text_color: "Hint"
                    
                MDLabel:
                    text: "Mobile: " + app.user_mobile
                    theme_text_color: "Hint"
                    
                # Ithe Age add kele ahe
                MDLabel:
                    text: "Age: " + app.user_age
                    theme_text_color: "Hint"

                MDSeparator:
                    height: "1dp"
                    
                MDLabel:
                    text: "Emergency Contacts"
                    font_style: "Subtitle1"
                    theme_text_color: "Custom"
                    text_color: app.theme_cls.primary_color
                    bold: True

                MDTextField:
                    id: contact_1
                    hint_text: "Mobile 1 (Family)"
                    mode: "rectangle"
                    input_filter: "int"
                    max_text_length: 10

                MDTextField:
                    id: contact_2
                    hint_text: "Mobile 2 (Family)"
                    mode: "rectangle"
                    input_filter: "int"
                    max_text_length: 10

                MDTextField:
                    id: contact_3
                    hint_text: "Mobile 3 (Family)"
                    mode: "rectangle"
                    input_filter: "int"
                    max_text_length: 10

                MDFillRoundFlatButton:
                    id: update_btn
                    text: "Save / Update Contacts"
                    pos_hint: {"center_x": .5}
                    size_hint_x: 1
                    md_bg_color: app.theme_cls.primary_color
                    on_release: app.update_contacts_profile()
                    
                Widget:
                    size_hint_y: None
                    height: "15dp"
                    
                MDFillRoundFlatButton:
                    text: "Log Out"
                    pos_hint: {"center_x": .5}
                    size_hint_x: 0.6
                    md_bg_color: 1, 0, 0, 1
                    on_release: app.log_out()
'''


def hash_password(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000).hex()


class SplashScreen(MDScreen):
    def on_enter(self, *args):
        Clock.schedule_once(self.start_animation, 0.1)

    def start_animation(self, dt):
        Animation(opacity=1, duration=1.5).start(self.ids.logo_label)
        Animation(opacity=1, duration=2.0).start(self.ids.dev_label)
        Clock.schedule_once(self.check_database, 3.5)

    def check_database(self, dt):
        app = MDApp.get_running_app()
        if app.store.exists("user"):
            app.root.current = "main"
            if app.store.exists("contacts"):
                app.hide_contacts_box()
        else:
            app.root.current = "signup"


class SignUpScreen(MDScreen):
    pass


class SignInScreen(MDScreen):
    pass


class MainScreen(MDScreen):
    pass


class ProfileScreen(MDScreen):
    def on_enter(self, *args):
        app = MDApp.get_running_app()
        self.ids.contact_1.text = app.em_contact_1
        self.ids.contact_2.text = app.em_contact_2
        self.ids.contact_3.text = app.em_contact_3


class AegisApp(MDApp):
    user_name = StringProperty("Not Set")
    user_mobile = StringProperty("Not Set")
    user_age = StringProperty("Not Set")
    em_contact_1 = StringProperty("")
    em_contact_2 = StringProperty("")
    em_contact_3 = StringProperty("")
    are_contacts_saved = BooleanProperty(False)

    countdown_time = 5
    dialog = None
    siren_sound = None
    timer_event = None
    flash_state = False
    store = None
    services_started = False
    cooldown_until = 0
    last_lat = None
    last_lon = None
    _contacts_box = None

    # ------------------------------------------------------------ lifecycle
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Cyan"
        # user_data_dir is the writable app folder on Android
        self.store = JsonStore(os.path.join(self.user_data_dir, "aegis_database.json"))
        return Builder.load_string(KV)

    def on_start(self):
        if self.store.exists("user"):
            user_data = self.store.get("user")
            self.user_name = user_data["name"]
            self.user_mobile = user_data["mobile"]
            self.user_age = user_data.get("age", "N/A")

        if self.store.exists("contacts"):
            contact_data = self.store.get("contacts")
            self.em_contact_1 = contact_data["c1"]
            self.em_contact_2 = contact_data["c2"]
            self.em_contact_3 = contact_data["c3"]
            self.are_contacts_saved = True

        if IS_ANDROID:
            request_permissions(
                [
                    Permission.SEND_SMS,
                    Permission.ACCESS_FINE_LOCATION,
                    Permission.ACCESS_COARSE_LOCATION,
                    Permission.CAMERA,  # needed for the flashlight
                ],
                self.on_permissions_result,
            )
        else:
            self.start_services(True)

    def on_pause(self):
        return True  # keep the app alive when it goes to the background

    def on_resume(self):
        pass

    def on_permissions_result(self, permissions, grants):
        location_ok = any(
            g for p, g in zip(permissions, grants) if "LOCATION" in p
        )
        Clock.schedule_once(lambda dt: self.start_services(location_ok), 0)

    def start_services(self, location_ok):
        if self.services_started or not has_sensor:
            return
        self.services_started = True
        try:
            accelerometer.enable()
            Clock.schedule_interval(self.check_sensor, SENSOR_INTERVAL)
        except Exception as e:
            print("Accelerometer unavailable:", e)
        if location_ok:
            try:
                gps.configure(on_location=self.on_gps_location, on_status=self.on_gps_status)
                gps.start(minTime=5000, minDistance=0)
            except Exception as e:
                print("GPS unavailable:", e)

    def on_gps_location(self, **kwargs):
        self.last_lat = kwargs.get("lat")
        self.last_lon = kwargs.get("lon")

    def on_gps_status(self, stype, status):
        pass

    # ------------------------------------------------------ fall detection
    def check_sensor(self, dt):
        if self.dialog is not None or time.time() < self.cooldown_until:
            return
        try:
            val = accelerometer.acceleration
        except Exception:
            return
        if not val or any(v is None for v in val):
            return
        if math.sqrt(sum(v * v for v in val)) > FALL_THRESHOLD:
            self.trigger_fall_detection()

    def trigger_fall_detection(self):
        self.countdown_time = 5
        self.cooldown_until = time.time() + COOLDOWN_SECONDS
        try:
            self.siren_sound = SoundLoader.load(SIREN_PATH)
            if self.siren_sound:
                self.siren_sound.loop = True
                self.siren_sound.play()
        except Exception:
            pass

        self.dialog = MDDialog(
            title="FALL DETECTED!",
            text=f"Sending Direct SMS, Audio & Flash SOS in {self.countdown_time} sec...",
            auto_dismiss=False,
            buttons=[
                MDFlatButton(
                    text="I AM SAFE (CANCEL)",
                    text_color=[1, 0, 0, 1],
                    on_release=self.cancel_sos,
                )
            ],
        )
        self.dialog.open()
        self.timer_event = Clock.schedule_interval(self.update_timer, 1)

    def update_timer(self, dt):
        self.countdown_time -= 1

        if has_sensor:
            try:
                if self.flash_state:
                    flashlight.off()
                else:
                    flashlight.on()
                self.flash_state = not self.flash_state
            except Exception:
                pass

        if self.dialog:
            self.dialog.text = (
                f"Sending Direct SMS, Audio & Flash SOS in {max(self.countdown_time, 0)} sec..."
            )

        if self.countdown_time <= 0:
            self.stop_alarm()
            self.execute_emergency_protocol()

    def stop_alarm(self):
        if self.timer_event:
            self.timer_event.cancel()
            self.timer_event = None
        if self.siren_sound:
            self.siren_sound.stop()
        if has_sensor:
            try:
                flashlight.off()
            except Exception:
                pass
        self.flash_state = False
        if self.dialog:
            self.dialog.dismiss()
            self.dialog = None

    def cancel_sos(self, instance):
        self.stop_alarm()
        self.cooldown_until = time.time() + COOLDOWN_SECONDS
        toast("SOS cancelled - glad you are safe!")

    def execute_emergency_protocol(self):
        try:
            bat_percent = f"{float(battery.status.get('percentage')):.0f}"
        except Exception:
            bat_percent = "Unknown"

        if self.last_lat is not None and self.last_lon is not None:
            location_link = f"https://maps.google.com/?q={self.last_lat},{self.last_lon}"
        else:
            location_link = "Location unavailable"

        msg = (
            "EMERGENCY: AEGIS detected a fall!\n"
            f"User: {self.user_name}\n"
            f"Battery: {bat_percent}%\n"
            f"Location: {location_link}"
        )

        contacts = [c for c in (self.em_contact_1, self.em_contact_2, self.em_contact_3) if c]
        if not contacts:
            toast("No emergency contacts saved!")
            return

        sent = 0
        for num in contacts:
            if self.send_sms(num, msg):
                sent += 1
        toast(f"Emergency SMS sent to {sent} of {len(contacts)} contacts")

    def send_sms(self, number, message):
        full_number = "+91" + number
        if not IS_ANDROID:
            print(f"[Desktop test] SMS to {full_number}: {message}")
            return True
        try:
            SmsManager = autoclass("android.telephony.SmsManager")
            sms = SmsManager.getDefault()
            parts = sms.divideMessage(message)
            sms.sendMultipartTextMessage(full_number, None, parts, None, None)
            return True
        except Exception as e:
            print("SMS failed:", e)
            return False

    # ---------------------------------------------------------- sign up/in
    def calculate_age(self, dob_text):
        if not dob_text:
            return
        try:
            birth_date = datetime.strptime(dob_text, "%Y-%m-%d")
            today = datetime.today()
            age = today.year - birth_date.year - (
                (today.month, today.day) < (birth_date.month, birth_date.day)
            )
            self.root.get_screen("signup").ids.age_input.text = f"{age} Years"
        except ValueError:
            pass

    def show_date_picker(self):
        date_dialog = MDDatePicker(year=2000, month=1, day=1)
        date_dialog.bind(on_save=self.on_save_date)
        date_dialog.open()

    def on_save_date(self, instance, value, date_range):
        signup_screen = self.root.get_screen("signup")
        signup_screen.ids.dob_input.text = str(value)
        self.calculate_age(str(value))

    def verify_signup(self):
        ids = self.root.get_screen("signup").ids
        name = ids.name_input.text.strip()
        mobile = ids.mobile_input.text.strip()
        password = ids.password_input.text

        if not name:
            return toast("Please enter your name")
        if len(mobile) != 10 or not mobile.isdigit():
            return toast("Enter a valid 10-digit mobile number")
        if len(password) < 8 or password.isdigit() or password.isalpha():
            return toast("Password: min 8 characters with letters and numbers")

        salt = os.urandom(16)
        self.user_name = name
        self.user_mobile = mobile
        self.user_age = ids.age_input.text or "N/A"
        self.store.put(
            "user",
            name=self.user_name,
            mobile=self.user_mobile,
            age=self.user_age,
            salt=salt.hex(),
            pw_hash=hash_password(password, salt),
        )
        self.root.current = "main"

    def verify_login(self):
        ids = self.root.get_screen("signin").ids
        if not self.store.exists("user"):
            return toast("No account found - please sign up")
        user = self.store.get("user")
        if "pw_hash" not in user:
            return toast("Please sign up again")
        attempt = hash_password(ids.login_password.text, bytes.fromhex(user["salt"]))
        if ids.login_mobile.text == user["mobile"] and hmac.compare_digest(attempt, user["pw_hash"]):
            self.root.current = "main"
        else:
            toast("Wrong mobile number or password")

    # ------------------------------------------------------------ contacts
    def hide_contacts_box(self):
        main_screen = self.root.get_screen("main")
        box = main_screen.ids.contacts_box
        if box in main_screen.ids.main_layout.children:
            self._contacts_box = box
            main_screen.ids.main_layout.remove_widget(box)
        self.are_contacts_saved = True

    def _valid_numbers(self, *numbers):
        return all(n == "" or (len(n) == 10 and n.isdigit()) for n in numbers)

    def save_contacts_main(self):
        ids = self.root.get_screen("main").ids
        c1, c2, c3 = (ids.main_contact_1.text, ids.main_contact_2.text, ids.main_contact_3.text)
        if not (c1 or c2 or c3):
            return toast("Enter at least one number")
        if not self._valid_numbers(c1, c2, c3):
            return toast("Numbers must be 10 digits")
        self.em_contact_1, self.em_contact_2, self.em_contact_3 = c1, c2, c3
        self.store.put("contacts", c1=c1, c2=c2, c3=c3)
        if not self.are_contacts_saved:
            self.hide_contacts_box()
        toast("Contacts saved")

    def update_contacts_profile(self):
        profile_screen = self.root.get_screen("profile")
        c1, c2, c3 = (
            profile_screen.ids.contact_1.text,
            profile_screen.ids.contact_2.text,
            profile_screen.ids.contact_3.text,
        )
        if not self._valid_numbers(c1, c2, c3):
            return toast("Numbers must be 10 digits")
        self.em_contact_1, self.em_contact_2, self.em_contact_3 = c1, c2, c3
        self.store.put("contacts", c1=c1, c2=c2, c3=c3)
        profile_screen.ids.update_btn.text = "Updated Successfully!"
        profile_screen.ids.update_btn.md_bg_color = [0, 0.8, 0, 1]
        Clock.schedule_once(lambda dt: self.reset_update_btn(), 2)

    def reset_update_btn(self):
        profile_screen = self.root.get_screen("profile")
        profile_screen.ids.update_btn.text = "Save / Update Contacts"
        profile_screen.ids.update_btn.md_bg_color = self.theme_cls.primary_color

    # ---------------------------------------------------------- navigation
    def open_profile(self):
        self.root.current = "profile"

    def go_back_to_main(self):
        self.root.current = "main"

    def log_out(self):
        self.store.clear()
        self.user_name = self.user_mobile = self.user_age = "Not Set"
        self.em_contact_1 = self.em_contact_2 = self.em_contact_3 = ""
        # bring the "Add Emergency Contacts" box back for the next user
        main_screen = self.root.get_screen("main")
        layout = main_screen.ids.main_layout
        if self._contacts_box is not None and self._contacts_box not in layout.children:
            layout.add_widget(self._contacts_box, index=len(layout.children))
        for field in ("main_contact_1", "main_contact_2", "main_contact_3"):
            main_screen.ids[field].text = ""
        self.are_contacts_saved = False
        self.root.current = "signup"

    # ------------------------------------------------------------- actions
    def call_108(self):
        # Opens the phone dialer with 108 already typed in
        webbrowser.open("tel:108")

    def find_hospital(self):
        if IS_ANDROID:
            webbrowser.open("geo:0,0?q=hospitals+near+me")
        else:
            webbrowser.open("https://www.google.com/maps/search/hospitals+near+me")


if __name__ == "__main__":
    AegisApp().run()
