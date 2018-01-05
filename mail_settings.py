def config_email(app):
    app.config.update(
        DEBUG=True,
        # EMAIL SETTINGS
        MAIL_SERVER='smtp.gmail.com',
        MAIL_PORT=465,
        MAIL_USE_SSL=True,
        MAIL_USERNAME='verbovelocity@gmail.com',
        MAIL_PASSWORD='teamnerck'
    )