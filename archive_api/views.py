# Create your views here.
from django.contrib.auth.decorators import login_required
from django.http import (
    Http404, HttpResponseRedirect,
)
from django.shortcuts import render, get_object_or_404

# Create your views here.

from archive_api.models import DataSet


def doi(request, ngt_id):
    """
    Public doi pages
    :param request:
    :return:
    """

    dataset = get_object_or_404(DataSet, ngt_id=int(ngt_id[3:]))

    if (dataset.status == DataSet.STATUS_APPROVED and \
                    dataset.access_level == DataSet.ACCESS_PUBLIC):
        author_list = ["{} {}".format(o.last_name, o.first_name) for o in dataset.authors.all()]
        authors = ", ".join(author_list)
        author_list = ["{} {}".format(o.last_name, o.first_name[0]) for o in dataset.authors.all()]
        authors_initial = ", ".join(author_list)

        site_id_list = [o.site_id for o in dataset.sites.all()]
        site_ids = "; ".join(site_id_list)

        site_list = [o.name for o in dataset.sites.all()]
        sites = "; ".join(site_list)

        variable_list = [o.name for o in dataset.variables.all()]
        variables = "; ".join(variable_list)

        return render(request, 'archive_api/doi.html', context={'user': request.user,
                                                       'dataset': dataset,
                                                       'authors': authors,
                                                       'site_ids': site_ids,
                                                       'sites': sites,
                                                       'variables': variables,
                                                       'authors_initial': authors_initial})
    else:
        raise Http404('That dataset does not exist')


@login_required
def download(request, ngt_id):
    """
    Download the dataset

    :param request:
    :param ngt_id:
    :return:
    """

    dataset = get_object_or_404(DataSet, ngt_id=int(ngt_id[3:]))
    return HttpResponseRedirect("/api/v1/datasets/{}/archive".format(dataset.id))
