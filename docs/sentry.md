## Sentry

> Intro: What we offer

**Rocket Django PRO** can be integrated with Sentry for error tracking and performance monitoring of the application.

`Sentry` stands as a forefront platform dedicated to developers, providing essential capabilities in error tracking and performance monitoring. It serves as a pivotal tool for developers, offering insights and oversight into errors and performance issues within their applications. This developer-centric platform is designed to empower development teams with the necessary tools to detect, diagnose, and resolve errors efficiently, ensuring robust performance and enhanced user experiences.

### Integrating Rocket Django with Sentry

**Rocket Django PRO** uses the `Sentry SDK` package to connect the application to Sentry for monitoring. The configuration is found in `core/settings.py`.
```py
# core/settings.py
...
import sentry_sdk
...
sentry_sdk.init(
    dsn=os.getenv('DSN_KEY'),
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
)
```
The package requires a `DSN_KEY` that is an environmental variable to function properly. This can be obtained from Sentry's website. To add more customization options, check [Sentry Django](https://docs.sentry.io/platforms/python/integrations/django/) documentation.


### How to get Sentry's DSN Key

> How to use it

- Open https://sentry.io/ from your browser and create an account.

- After signing up, use the `Install Sentry` option from the page to start the setup of configuring your application for Sentry.

- Skip the onboarding tutorial. On the user dashboard, create a new project.

- Select Python as the platform you want to work with and Django as the framework. The next page shows how to set up Sentry for a Django application, and the set-up also contains the DSN key that is needed for our application.

- The set-up information will contain a similar script as the one below

```py
# settings.py
import sentry_sdk

sentry_sdk.init(
    dsn="https://******.ingest.sentry.io/******",
    ...
)

api = falcon.API()
```

Copy the value of the `dsn` attribute, create a `.env` file in the root directory and add the following credentials

```bash
DSN_KEY=https://******.ingest.sentry.io/******
```

Any error the application encounters will be recorded by Sentry, and you can use it to debug your application errors and monitor how your application is running.


## Conclusion
In conclusion, the integration of Sentry into Rocket Django PRO marks a significant enhancement in the development experience. With Sentry's robust error tracking and performance monitoring, developers can proactively address issues, ensuring a seamless and optimized application. Elevate your development journey with Rocket Django PRO and Sentry, where robustness meets insight for unparalleled performance.

## Resources
- 👉 [Sentry](https://docs.sentry.io/platforms/python/) Documentation
- 👉 [Rocket Django](https://docs.appseed.us/products/rocket/django/) product offering
- 👉 Join the [Community](https://discord.com/invite/fZC6hup) and chat with the team behind **Rocket Django**
