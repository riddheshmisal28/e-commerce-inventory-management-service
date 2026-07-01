from context_client import EngineeringContextClient
from models import EngineeringContext

client = EngineeringContextClient()

def retrieve_context(plan) -> EngineeringContext:
    context = EngineeringContext()

    if plan.need_entities:
        context.entities = client.get_entities()

    if plan.need_endpoints:
        context.endpoints = client.get_endpoints()

    if plan.need_models:
        context.models = client.get_models()

    return context