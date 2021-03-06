# Copyright 2018 Novo Nordisk Foundation Center for Biosustainability, DTU.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import logging
from aiohttp import web
import aiohttp_cors
from venom.rpc import Service, Venom
from venom.rpc.comms.aiohttp import create_app
from venom.rpc.method import http
from venom.rpc.reflect.service import ReflectService
from venom.fields import MapField, String
from venom.message import Message
from gene_to_reactions.ice_client import IceClient
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest, Histogram
from prometheus_client.multiprocess import MultiProcessCollector

from . import settings
from .middleware import raven_middleware


logger = logging.getLogger(__name__)

# REQUEST_TIME: Time spent waiting for outgoing API request to internal or external services
# labels:
#   service: The current service (always 'gene-to-reactions')
#   environment: The current runtime environment ('production' or 'staging')
#   endpoint: The path to the requested endpoint without query parameters (e.g. '/annotation/genes')
REQUEST_TIME = Histogram('decaf_request_handler_duration_seconds', "Time spent in request", ['service', 'environment', 'endpoint'])

class GeneMessage(Message):
    gene_id = String(description='Gene identifier')


class AnnotationMessage(Message):
    response = MapField(str, description='Reactions identifiers mapped to reaction strings')


class AnnotationService(Service):
    class Meta:
        name = 'gene-to-reactions/annotation'

    @http.GET('./genes',
              description='Return reactions for the given gene identifier. '
                          'Queries ICE library')
    async def reactions(self, request: GeneMessage) -> AnnotationMessage:
        with REQUEST_TIME.labels(service='gene-to-reactions', environment=settings.ENVIRONMENT,
                             endpoint='/annotation/genes').time():
            result = await IceClient().reaction_equations(request.gene_id)
            return AnnotationMessage(response=result)

async def metrics(request):
    resp = web.Response(body=generate_latest(MultiProcessCollector(CollectorRegistry())))
    resp.content_type = CONTENT_TYPE_LATEST
    return resp


venom = Venom(version='0.1.0', title='GenesToReactions')
venom.add(AnnotationService)
venom.add(ReflectService)
app = create_app(venom, web.Application(middlewares=[raven_middleware]))
app.router.add_get("/metrics", metrics)
# Configure default CORS settings.
cors = aiohttp_cors.setup(app, defaults={
    "*": aiohttp_cors.ResourceOptions(
        expose_headers="*",
        allow_headers="*",
        allow_credentials=True,
    )
})


# Configure CORS on all routes.
for route in list(app.router.routes()):
    cors.add(route)


async def start(loop):
    await loop.create_server(app.make_handler(), '0.0.0.0', 8000)
    logger.info('Web server is up')


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start(loop))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
