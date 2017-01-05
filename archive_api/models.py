import mimetypes

import os
from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage
from django.db import models
from rest_framework.exceptions import ValidationError


class DatasetArchiveField( models.FileField):


        CONTENT_TYPES = ["application/zip", "application/x-bzip2",
                     "application/gzip", "application/x-lzip", "application/x-lzma",
                     "application/x-xz", "application/x-compress",
                     "application/x-compress", "application/x-7z-compressed",
                     "application/x-gtar", "application/x-rar-compressed"]

        def __init__(self, *args, **kwargs):
            """
            Override the parent constructor to set the allowed content_types

            :param args:
            :param kwargs:
            """

            self.content_types = self.CONTENT_TYPES
            super(DatasetArchiveField,self).__init__(*args,**kwargs)

        def clean(self, *args, **kwargs):
            """
            Override parent method to add checking for content type

            Parent method converts the value's type and run validation. Validation errors
            from to_python and validate are propagated. The correct value is
            returned if no error is raised.
            """
            data = super(DatasetArchiveField,self).clean(*args,**kwargs)

            try:
                content_type = mimetypes.guess_type(data.name)
                if content_type[0] not in self.content_types:
                    raise ValidationError('Filetype {} not supported. Allowed types: {}'.format(content_type[0],
                                                                                                ", ".join(
                                                                                                  self.content_types)))
            except AttributeError:
                raise ValidationError('Filetype unknown. Allowed types: {}'.format(", ".join(self.content_types)))

        def save(self, **kwargs):
            """
            Override parent to call the custom clean method

            :param kwargs:
            :return:
            """
            return super(DatasetArchiveField, self).save(**kwargs)


class DatasetArchiveStorage(FileSystemStorage):

    def __init__(self,*args, **kwargs):
        """
        Override parent constructor. If location is not set, set the
        `DATASET_ARCHIVE_ROOT`

        See `django.core.files.storage.FileSystemStorage` for more details.

        :param args:
        :param kwargs:
        """

        from django.conf import settings
        if "location" not in kwargs:
            kwargs["location"]=settings.DATASET_ARCHIVE_ROOT
        if "base_url" not in kwargs:
            kwargs["base_url"] = settings.DATASET_ARCHIVE_URL
        super(DatasetArchiveStorage, self).__init__(*args, **kwargs)


dataset_archive_storage = DatasetArchiveStorage()


STATUS_CHOICES = (
    ('0', 'Draft'),
    ('1', 'Submitted'),
    ('2', 'Approved'),
)

QAQC_STATUS_CHOICES = (
    ('0', 'None'),
    ('1', 'Preliminary QA-QC'),
    ('2', 'Full QA-QC'),
)

ACCESS_CHOICES = (
    ('0', 'Private'),
    ('1', 'NGEE Tropics'),
    ('2', 'Public'),
)


def get_upload_path(instance, filename):
    """
    This generates the file upload path
    :param instance:
    :param filename:
    :return:
    """
    _, file_extension = os.path.splitext(filename)
    return os.path.join(
        "{}_{}{}".format(instance.data_set_id(), instance.version, file_extension))


class MeasurementVariable(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return '<Contact {}>'.format(self)


class Person(models.Model):
    first_name = models.CharField(max_length=50, blank=False)
    last_name = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    institution_affiliation = models.CharField(max_length=100, blank=True)

    class Meta:
        unique_together = ('first_name', 'last_name', 'institution_affiliation', 'email')
        ordering = ('last_name', 'first_name',)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return '{}, {} - {}'.format(self.last_name, self.first_name, self.institution_affiliation)

    def __repr__(self):
        return '<Contact {}>'.format(self)


class Site(models.Model):
    site_id = models.CharField(unique=True, max_length=30)
    name = models.CharField(unique=True, max_length=300)
    description = models.TextField()
    country = models.CharField(max_length=100, blank=True)
    state_province = models.CharField(max_length=100, blank=True)
    utc_offset = models.IntegerField(blank=True, null=True)
    location_latitude = models.FloatField(blank=True, null=True)
    location_longitude = models.FloatField(blank=True, null=True)
    location_elevation = models.CharField(blank=True, max_length=30)
    location_map_url = models.URLField(blank=True, null=True)
    location_bounding_box_ul_latitude = models.FloatField(blank=True, null=True)
    location_bounding_box_ul_longitude = models.FloatField(blank=True, null=True)
    location_bounding_box_lr_latitude = models.FloatField(blank=True, null=True)
    location_bounding_box_lr_longitude = models.FloatField(blank=True, null=True)
    site_urls = models.TextField(blank=True, null=True)
    contacts = models.ManyToManyField(Person)
    pis = models.ManyToManyField(Person, related_name='+')
    submission = models.ForeignKey(Person, on_delete=models.DO_NOTHING, related_name='+')
    submission_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return '{} - {}'.format(self.site_id, self.name)

    def __repr__(self):
        return '<Site {}>'.format(self)


class Plot(models.Model):
    plot_id = models.CharField(max_length=30, unique=True)
    name = models.CharField(unique=True, max_length=150)
    description = models.TextField()
    size = models.CharField(max_length=100, blank=True, null=True, )
    location_elevation = models.CharField(blank=True, null=True, max_length=30)
    location_kmz_url = models.URLField(blank=True, null=True, )
    pi = models.ForeignKey(Person, on_delete=models.DO_NOTHING, blank=True, null=True)
    site = models.ForeignKey(Site, on_delete=models.DO_NOTHING)
    submission = models.ForeignKey(Person, on_delete=models.DO_NOTHING, related_name='+')
    submission_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return '{} - {}'.format(self.site.site_id, self.plot_id)

    def __repr__(self):
        return '<Plot {}>'.format(self)


class DataSet(models.Model):

    def data_set_id(self):
        return "NGT{:04}".format(self.id)

    description = models.TextField(blank=True, null=True)
    version = models.CharField(max_length=15, default="1.0")

    status = models.CharField(max_length=1, choices=STATUS_CHOICES,
                              default='0')  # (draft [DEFAULT], submitted, approved)
    status_comment = models.TextField(blank=True, null=True)
    name = models.CharField(unique=True, max_length=150, blank=True, null=True)
    doi = models.TextField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    qaqc_status = models.CharField(max_length=1, choices=QAQC_STATUS_CHOICES, blank=True, null=True)
    qaqc_method_description = models.TextField(blank=True, null=True)
    ngee_tropics_resources = models.BooleanField(default=False)
    funding_organizations = models.TextField(blank=True, null=True)
    doe_funding_contract_numbers = models.CharField(max_length=100, blank=True, null=True)
    acknowledgement = models.TextField(blank=True, null=True)
    reference = models.TextField(blank=True, null=True)
    additional_reference_information = models.TextField(blank=True, null=True)
    originating_institution = models.TextField(blank=True, null=True)

    access_level = models.CharField(max_length=1, choices=ACCESS_CHOICES, default='0')
    additional_access_information = models.TextField(blank=True, null=True)
    submission_date = models.DateField(blank=True, null=True)

    # Owner is the person who created the dataset
    created_by = models.ForeignKey(User, editable=False, related_name='+')
    created_date = models.DateTimeField(editable=False, auto_now_add=True)
    modified_by = models.ForeignKey(User, editable=False, related_name='+')
    modified_date = models.DateTimeField(editable=False, auto_now=True)

    # Relationships
    authors = models.ManyToManyField(Person, blank=True, related_name='+', through='Author')
    contact = models.ForeignKey(Person, on_delete=models.DO_NOTHING, blank=True, null=True)
    sites = models.ManyToManyField(Site, blank=True)
    plots = models.ManyToManyField(Plot, blank=True)
    variables = models.ManyToManyField(MeasurementVariable, blank=True)

    # CDIAC Import Fields
    cdiac_import = models.BooleanField(default=False)
    cdiac_submission_contact = models.ForeignKey(Person, related_name='+', on_delete=models.DO_NOTHING, blank=True,
                                                 null=True)

    archive = DatasetArchiveField(upload_to=get_upload_path, storage=dataset_archive_storage, null=True)

    class Meta:
        permissions = (
            ("approve_submitted_dataset", "Can approve a 'submitted' dataset"),
            ("edit_draft_dataset", "Can edit a 'draft' dataset"),
            ("unsubmit_submitted_dataset", "Can unsubmit a 'submitted' dataset"),
            ("unapprove_approved_dataset", "Can unapprove a 'approved' dataset"),
            ("delete_draft_dataset", "Can delete a 'draft' dataset"),
            ("delete_submitted_dataset", "Can delete a 'submitted' dataset")
        )


class Author(models.Model):
    """ Model for storing data about the Author relationship between DataSet and Person """
    author = models.ForeignKey(Person)
    dataset = models.ForeignKey(DataSet)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('dataset', 'order', 'author')
        ordering = ('dataset', 'order')