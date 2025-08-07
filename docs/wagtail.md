## Wagtail CMS

> Intro: What we offer

**Rocket Django PRO** allows you to engage with your website audience using blog content. Rocket Django PRO offers content management capabilities using `Wagtail CMS`.

`Wagtail CMS` is an open-source content management system (CMS) constructed on Django. It has earned popularity for its robust features and user-friendly interface, offering a seamless editing experience. Wagtail presents an extensive toolkit for content creation and management, encompassing a feature-rich text editor with formatting capabilities, efficient image and document handling, version control, workflows, and content scheduling.

### How to add blog posts

> How to use it

- To access the Wagtail admin dashboard open http://127.0.0.1:8000/cms-admin/ from your browser. You need to be signed in to access the Dashboard.

![Wagtail CMS Dashboard](https://github.com/app-generator/dummy/assets/57325382/c0bc342c-e416-40d6-b93f-508ca1a5044f)

- You can add different blog categories from the `snippets` menu on the sidebar, or by visiting http://127.0.0.1:8000/cms-admin/snippets/cms/category/ directly.

![Wagtail CMS Categories page](https://github.com/app-generator/dummy/assets/57325382/281d2d23-ba08-443d-9e10-ec2e2aba5c11)

- To add blog content, visit the `pages` menu from the sidebar. This will bring out the list of sites registered. Hover on the site and use the `Add child page` option to create new content.

![Wagtail Site Pages](https://github.com/app-generator/dummy/assets/57325382/6c838546-a80c-4980-875e-1630792eeb70)

- Any post published can be accessible from the `CMS` menu on the sidebar of the application, or by visiting the link http://127.0.0.1:8000/cms/ directly.

![Rocket Django CMS page](https://github.com/app-generator/dummy/assets/57325382/0fe37812-f596-4738-a835-cf0823a2542b)

![Rocket Django published blog](https://github.com/app-generator/dummy/assets/57325382/c1835e4a-5af6-48fe-a05f-50cd6eb5a2cd)

### How to customize Wagtail CMS

> Codebase: related app, model, template, js 

**Rocket Django PRO** integrates Wagtail CMS as a Django application. The application can be found in the `apps/cms` folder. The model for categories and blog posts can be found in `apps/cms/models.py`.

```py
from django.db import models
from django.utils import timezone
from wagtail.snippets.models import register_snippet
from wagtail.models import Page
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from django.contrib.auth.models import User


@register_snippet
class Category(models.Model):
    """A model representing a blog category."""
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class BlogPage(Page):
    """A model representing a blog page."""

    # Blog fields
    ...
    short_content = models.TextField(null=True, blank=True)
    content = RichTextField(null=True, blank=True)
    publishing_date = models.DateTimeField("Publishing Date", default=timezone.now)

    content_panels = Page.content_panels + [
        FieldPanel('author'),
        FieldPanel('thumbnail'),
        FieldPanel('category'),
        FieldPanel('short_content'),
        FieldPanel('content'),
        FieldPanel('publishing_date'),
    ]

    template = "apps/cms/blog_details.html"
```

The `Category` model is used to add categories to the blog posts. The `@register_snippet` decorator ensures the model is added as a model for a snippet. The `BlogPage` model is used to define the fields that should be present when creating a blog post. To learn more about how you can customize the Wagtail page models visit the [Wagtail Page Model](https://docs.wagtail.org/en/stable/topics/pages.html) Documentation page.

The templates for the blog post are located in the `templates/apps/cms` folder. `blog_list.html` Lists the blog post that has been published in the `cms` section of **Rocket Django PRO**. `blog_details.html` outlines how the blog posts from the model should be displayed. These templates can be defined to suit your project needs.

## Conclusion
Customizing Wagtail CMS in Rocket Django PRO provides a flexible and powerful solution for managing blog content. Elevate your website engagement with seamless content creation and management using Wagtail CMS.

## Resources
- 👉 [Wagtail CMS](https://docs.wagtail.org/en/stable/index.html) Documentation
- 👉 [Rocket Django](https://docs.appseed.us/products/rocket/django/) product offering
- 👉 Join the [Community](https://discord.com/invite/fZC6hup) and chat with the team behind **Rocket Django**
