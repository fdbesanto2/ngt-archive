# Create your views here.
from django.conf import settings
from django.views.generic import TemplateView


# Create your views here.


class IndexView(TemplateView):
    template_name = 'ui/index.html'

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        context['google_maps_key'] = settings.GOOGLE_MAPS_KEY

        return context





