from pyramid.config import Configurator


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.add_route('root','/')
    config.scan()
    app = config.make_wsgi_app()
    return app

