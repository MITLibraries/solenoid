from django.db import models

class Record(models.Model):
    """The Record contains:
        * citation information for an MIT author publication
        * plus all of the other data from Elements we will need to construct an
          email
        * plus any local recordkeeping we are doing about status (i.e. have we
          already solicited the author for this citation)."""

    class Meta:
        ordering = ['-name']

    ACQ_METHODS = (
        (0, 'RECRUIT_FROM_AUTHOR_MANUSCRIPT')
        #(1, FPV)
    )

    dlc = models.CharField(max_length=100)
    email = models.EmailField(help_text="Author email address")
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=40)
    publisher_name = models.CharField(max_length=50)
    acq_method = models.IntegerField(choices=ACQ_METHODS)
    citation = models.TextField()
    guidance = models.TextField(blank=True)

    ## I don't need ANY of these if I can get full citation.
    #title = models.TextField()
    #journal = models.TextField()
    ## In theory the following fields should be integers, but in practice, let's
    ## not trust unfamiliar metadata
    #volume = models.CharField(max_length=6, blank=True, null=True)
    #issue = models.CharField(max_length=3, blank=True, null=True)
    #year_published = models.DateField()
