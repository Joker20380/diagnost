from .forms import SubscriberForm


def subscriber_form(request):
    return {'subscriber_form': SubscriberForm()}