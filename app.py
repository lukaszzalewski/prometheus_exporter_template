from flask import Flask, escape, request
from logging.config import dictConfig
from prometheus_flask_exporter import PrometheusMetrics, is_running_from_reloader, current_app, choose_encoder, Gauge, Histogram
from prometheus_client import Enum, Info, Summary

import requests
import json
import os

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': os.environ.get('LOG_LEVEL', 'INFO'),
        'handlers': ['wsgi']
    }
})

app = Flask(__name__)

class PrometheusMetricsWithExporter(PrometheusMetrics):

    def register_endpoint(self, path, app):
        """
        Register the metrics endpoint on the Flask application.

        :param path: the path of the endpoint
        :param app: the Flask application to register the endpoint on
            (by default it is the application registered with this class)
        """

        if is_running_from_reloader() and not os.environ.get('DEBUG_METRICS'):
            return

        if app is None:
            app = self.app or current_app

        @self.do_not_track()
        def prometheus_metrics():
            # import these here so they don't clash with our own multiprocess module
            from prometheus_client import multiprocess, CollectorRegistry

            if 'PROMETHEUS_MULTIPROC_DIR' in os.environ or 'prometheus_multiproc_dir' in os.environ:
                registry = CollectorRegistry()
            else:
                registry = self.registry

            if 'name[]' in request.args:
                registry = registry.restricted_registry(request.args.getlist('name[]'))

            if 'PROMETHEUS_MULTIPROC_DIR' in os.environ or 'prometheus_multiproc_dir' in os.environ:
                multiprocess.MultiProcessCollector(registry)

            generate_metrics()

            generate_latest, content_type = choose_encoder(request.headers.get("Accept"))
            headers = {'Content-Type': content_type}
            return generate_latest(registry), 200, headers

        # apply any user supplied decorators, like authentication
        if self._metrics_decorator:
            prometheus_metrics = self._metrics_decorator(prometheus_metrics)

        # apply the Flask route decorator on our metrics endpoint
        app.route(path)(prometheus_metrics)

@app.route('/')
def homepage():
    return '<a href="/metrics">Metrics</a>'

metrics = PrometheusMetricsWithExporter(app, path='/metrics')
# Set the metric info
metrics.info('status_exporter', 'exports app status page for ingestion by prometheus', version='1.0.0')
by_path_counter = metrics.counter(
    'by_path_counter', 'Request count by request paths',
    labels={'path': lambda: request.path}
)

# Environmental Attributes set from the command line
# status data endpoints
APP_ENDPOINT = os.environ.get('CLOUDFLARE_SUMMARY', 'https://endpoint.app.com')

# prometheus metrics
status = Info('app_status_info','contains various information about the summary endpoint')

@app.before_first_request
def initiate_parser():
    '''
    any code that needs to execute before the first request is served
    '''

    app.logger.info('initiating parser')

def generate_metrics():
    '''
    code that generates data for the status endpoint. This will run when /metrics is visited
    '''

    app.logger.info('parseing metrics')
