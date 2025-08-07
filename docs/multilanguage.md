## Multilanguage

> Intro: What we offer

Imagine a single web application seamlessly adapting its content to speak the language and resonate with the unique preferences of every user. Craft immersive experiences that resonate with every user, regardless of their language. **Rocket Django PRO** offers multilanguage support for English, German and Italian. This is done using Django's internalization and localization feature.


### Adding localization with Rocket Django PRO

> How to use it 

This feature is currently supported in the `i18n.html` page, which is accessible via http://localhost:8000/i18n/

- The languages that are supported are defined in `core/settings.py`. Only languages listed in the `LANGUAGES` setting can be selected.
```py
# core/settings.py
from django.utils.translation import gettext_lazy as _
...
LANGUAGES = [
    ('en', _('English (US)')),
    ('de', _('Deutsch')),
    ('it', _('Italiano')),
]
```

- Load `i18n` on the page you want to add the translation option. For this documentation, we will be using `templates/pages/i18n.html`
```jinja
<!--templates/pages/i18n.html-->
{% load i18n %}
```
- Wrap the translatable content with `{% trans CONTENT_NAME %}`
```
<li class="flex items-center">
    <svg class="w-3.5 h-3.5 mr-2 text-green-500 dark:text-green-400 flex-shrink-0" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 20 20">
        <path d="M10 .5a9.5 9.5 0 1 0 9.5 9.5A9.51 9.51 0 0 0 10 .5Zm3.707 8.207-4 4a1 1 0 0 1-1.414 0l-2-2a1 1 0 0 1 1.414-1.414L9 10.586l3.293-3.293a1 1 0 0 1 1.414 1.414Z"/>
    </svg>
    {% trans "test4" %}
</li>
```
`test4` serves as an identifier that will be used to supply the content of the page in different languages.

- From your terminal, run the command below
```bash
$ django-admin makemessages -a
```
This command will create a new message file for each of the languages specified in `core/settings.py`. Message files can be found in `locale/<LANGUAGE_SHORTCODE>/LC_MESSAGES/django.po`. For example, English will be found in `locale/en/LC_MESSAGES/django.po` and German in `locale/de/LC_MESSAGES/django.po`.

- If you intend to create the message file for a specific language, use the command
```bash
$ django-admin makemessages -l <LANGUAGE_SHORTCODE>
```

- To add the content for `test4`, open the message files for each language and search for `test4`. Make the following changes to the `msgstr`.
```
# locale/en/LC_MESSAGES/django.po
#: templates/pages/i18n.html:32
msgid "test4"
msgstr "Thank you for following"
```

```
# locale/de/LC_MESSAGES/django.po
#: templates/pages/i18n.html:32
msgid "test4"
msgstr "Danke fürs Folgen"
```

```
# locale/it/LC_MESSAGES/django.po
#: templates/pages/i18n.html:32
msgid "test4"
msgstr "grazie per aver seguito"
```

- `msgid`: This is the original translation string as it appears in the source. Keep it unchanged.
- `msgstr`: Your language-specific translation goes here. Initially, it's empty, and it's up to you to fill it in. Remember to maintain the quotes around your translated text for accuracy.
    
As a convenience, each message includes, in the form of a comment line prefixed with `#` and located above the msgid line, the filename and line number from which the translation string was gleaned.


- After you create your message file – and each time you make changes to it – you’ll need to compile it to allow Django to use the translations in your website. Run the command below to compile the message files
```bash
$ django-admin compilemessages
```

This tool runs over all available `.po` files and creates `.mo` files, which are binary files optimized for use by `gettext`.

- Visit http://127.0.0.1:8000/i18n/ and use the language option at the bottom of the sidebar to change the language and see the translations for each language option.

![Rocket Django - Styled with Tailwind-Flowbite AppSeed - i18n page English text](https://github.com/app-generator/dummy/assets/57325382/7ba2da39-143e-4e13-96d2-6ed0c23edc58)

![Rocket Django - Styled with Tailwind-Flowbite AppSeed - i18n page German text](https://github.com/app-generator/dummy/assets/57325382/501f881d-9c9c-45be-991b-fccf78b98933)

![Rocket Django - Styled with Tailwind-Flowbite AppSeed - i18n page Italian text](https://github.com/app-generator/dummy/assets/57325382/024b25ef-1a23-4e14-ae03-83dec2621ab7)


## Conclusion
Ready to unlock the power of multilingual web experiences? Unlock the power of internationalization and localization to transform your web application into a global storyteller! With Rocket Django PRO's seamless localization, you're not just translating words, you're building bridges to an entire world of users.


## ✅ Resources
- 👉 [Django i18n](https://docs.djangoproject.com/en/4.2/topics/i18n/) Documentation
- 👉 [Django i18n Translation](https://docs.djangoproject.com/en/4.2/topics/i18n/translation/) Documentation
- 👉 [Rocket Django](https://docs.appseed.us/products/rocket/django/) product offering
- 👉 Join the [Community](https://discord.com/invite/fZC6hup) and chat with the team behind **Rocket Django**
