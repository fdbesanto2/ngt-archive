# Create your views here.
import inspect
from collections import OrderedDict

import os
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django.utils.encoding import smart_str
from rest_framework import permissions
from rest_framework import status
from rest_framework.decorators import detail_route
from rest_framework.exceptions import ValidationError
from rest_framework.metadata import SimpleMetadata
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from types import FunctionType

from archive_api.models import DataSet, MeasurementVariable, Site, Person, Plot, DatasetArchiveField
from archive_api.permissions import HasArchivePermission, HasSubmitPermission, HasApprovePermission, \
    HasUnsubmitPermission, \
    HasUnapprovePermission, HasUploadPermission, HasEditPermissionOrReadonly, APPROVED, DRAFT, SUBMITTED
from archive_api.serializers import DataSetSerializer, MeasurementVariableSerializer, SiteSerializer, PersonSerializer, \
    PlotSerializer


class DataSetMetadata(SimpleMetadata):
    def determine_metadata(self, request, view):
        """ Customize metadata from OPTIONS method to add detail_route information"""

        data = super(DataSetMetadata, self).determine_metadata(request, view)

        for x, y in view.__class__.__dict__.items():
            if type(y) == FunctionType and hasattr(y, "detail"):
                data.setdefault("detail_routes", default=OrderedDict())
                data["detail_routes"].setdefault(x, default=OrderedDict())
                detail_route = data["detail_routes"][x]
                detail_route["allowed_methods"] = y.bind_to_methods
                detail_route["description"] = inspect.getdoc(y)  # get clean text

        upload_route = data["detail_routes"]["upload"]
        upload_route["parameters"] = {"attachment": {
            "type": "file",
            "required": True,
            "allowed_mime_types": DatasetArchiveField.CONTENT_TYPES
        }}

        return data


class DataSetViewSet(ModelViewSet):
    """
        Returns a list of all  DataSets available to the archive_api service
    """
    permission_classes = (HasEditPermissionOrReadonly, permissions.IsAuthenticated)
    queryset = DataSet.objects.all()
    serializer_class = DataSetSerializer
    http_method_names = ['get', 'post', 'put', 'delete', 'head', 'options']
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    metadata_class = DataSetMetadata

    def perform_create(self, serializer):
        """
        Override the update method to update the created_by and modified by fields.]
        """
        if self.request.user.is_authenticated and serializer.is_valid():
            serializer.save(created_by=self.request.user, modified_by=self.request.user)

    def perform_update(self, serializer):
        """
        Override the update method to update the modified by fields.
        """
        if self.request.user.is_authenticated and serializer.is_valid():
            serializer.save(modified_by=self.request.user)

    @detail_route(methods=['GET'],
                  permission_classes=(HasEditPermissionOrReadonly, permissions.IsAuthenticated, HasArchivePermission))
    def archive(self, request, pk=None):

        dataset = self.get_object()

        from django.conf import settings
        # We want the current name of the Dataset as the files name
        dataset_name = dataset.name.replace(" ", "_")
        dataset_name = ''.join([i for i in dataset_name if i.isalnum() or i == "_"])
        dataset_name = dataset_name.replace("__", "_")
        dataset_id_version, file_extension = os.path.splitext(dataset.archive.name)

        fullpath = os.path.join(settings.DATASET_ARCHIVE_ROOT, dataset.archive.name)
        if not dataset.archive:
            return Response({'success': False, 'detail': 'Not found'},
                            status=status.HTTP_404_NOT_FOUND)

        response = HttpResponse()
        response['X-Sendfile'] = smart_str(fullpath)
        response['Content-Disposition'] = 'attachment; filename={}_{}_{}{}'.format(
            dataset.data_set_id(), dataset.version, dataset_name, file_extension)
        return response

    @detail_route(methods=['post'],
                  permission_classes=(HasEditPermissionOrReadonly, permissions.IsAuthenticated, HasUploadPermission))
    def upload(self, request, *args, **kwargs):
        """
        Upload an archive file to the Dataset
        """
        if 'attachment' in request.data:
            dataset = self.get_object()
            upload = request.data['attachment']

            try:
                # This will rollback the transaction on failure
                with transaction.atomic():
                    # Validate the archive field with clean()
                    dataset.archive.field.clean(upload, dataset)
                    dataset.archive.save(upload.name, upload)
            except ValidationError as ve:
                return Response({'success': False, 'detail': ve.detail},
                                status=status.HTTP_400_BAD_REQUEST)

            return Response({'success': True, 'detail': 'File uploaded'},
                            status=status.HTTP_201_CREATED, headers={'Location':
                                                                         dataset.archive.url})
        else:
            return Response({'success': False, 'detail': 'There is no file to upload'},
                            status=status.HTTP_400_BAD_REQUEST)

    @detail_route(methods=['post', 'get'],
                  permission_classes=(HasEditPermissionOrReadonly, permissions.IsAuthenticated, HasApprovePermission))
    def approve(self, request, pk=None):
        """
        Approve action.  Changes the dataset from SUBMITTED to APPROVED status. User must permissions for this action
        """

        self.change_status(request, APPROVED)
        return Response({'success': True, 'detail': 'DataSet has been approved.'}, status=status.HTTP_200_OK)

    @detail_route(methods=['post', 'get'],
                  permission_classes=(HasEditPermissionOrReadonly, permissions.IsAuthenticated, HasUnsubmitPermission))
    def unsubmit(self, request, pk=None):
        """
        Unsubmit action.  Changes the dataset from SUBMITTED to DRAFT status. User must have permissions for this action
        """

        self.change_status(request, DRAFT)
        return Response({'success': True, 'detail': 'DataSet has been unsubmitted.'}, status=status.HTTP_200_OK)

    @detail_route(methods=['post', 'get'],
                  permission_classes=(
                          HasEditPermissionOrReadonly, permissions.IsAuthenticated, HasUnapprovePermission))
    def unapprove(self, request, pk=None):
        """
        Unapprove action.  Changes the dataset from APPROVED to SUBMITTED status. User must have permissions for this action
        """

        self.change_status(request, SUBMITTED)
        return Response({'success': True, 'detail': 'DataSet has been unapproved.'}, status=status.HTTP_200_OK)

    @detail_route(methods=['post', 'get'],
                  permission_classes=(HasEditPermissionOrReadonly, permissions.IsAuthenticated, HasSubmitPermission))
    def submit(self, request, pk=None):
        """
        Submit action. Changes the dataset from DRAFT to SUBMITTED status. User must have permissions for this action.
        """
        self.change_status(request, SUBMITTED)
        return Response({'success': True, 'detail': 'DataSet has been submitted.'}, status=status.HTTP_200_OK)

    def change_status(self, request, status):
        """
        Change the status of the dataset. This will raise and exception on ValidationErrors and
        invalid permissions.
        """
        dataset = self.get_object()  # this will initiate a permissions check
        dataset.status = status
        dataset.submission_date = timezone.now()
        serializer = DataSetSerializer(dataset, context={'request': request})
        deserializer = DataSetSerializer(dataset, data=serializer.data, context={'request': request})
        deserializer.is_valid(raise_exception=True)
        self.perform_update(deserializer)


class MeasurementVariableViewSet(ModelViewSet):
    """
        Returns a list of all  Measurement Variables available to the archive_api service
    """
    queryset = MeasurementVariable.objects.all()
    serializer_class = MeasurementVariableSerializer
    http_method_names = ['get', 'head', 'options']


class SiteViewSet(ModelViewSet):
    """
        Returns a list of all  Sites available to the archive_api service
    """
    queryset = Site.objects.all()
    serializer_class = SiteSerializer
    http_method_names = ['get', 'head', 'options']


class PersonViewSet(ModelViewSet):
    """
        Returns a list of all  Persons available to the archive_api service

    """
    queryset = Person.objects.all()
    serializer_class = PersonSerializer
    http_method_names = ['get', 'post', 'put', 'head', 'options']


class PlotViewSet(ModelViewSet):
    """
        Returns a list of all Plots available to the archive_api service

    """
    queryset = Plot.objects.all()
    serializer_class = PlotSerializer
    http_method_names = ['get', 'head', 'options']