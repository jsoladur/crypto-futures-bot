from aiogram3_form import Form, FormField


class LoginForm(Form):
    username: str = FormField(enter_message_text="Enter username")
    password: str = FormField(enter_message_text="Enter password")
