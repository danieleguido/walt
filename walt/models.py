import re, os
from datetime import datetime

from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse
from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.utils.timezone import utc


#
#
#  PSEUDO FREE TAGS
#  ================
#
#
class Tag(models.Model):

  # feel free to add tag type to this model ... :D
  FREE = '' # i.e, no special category at all
  AUTHOR = 'Au'
  KEYWORD = 'Ke'
  INSTITUTION = 'In'
  RESEARCHER = 'Rs'
  PLACE = 'Pl'
  DATE = 'Da'
  GEOCOVER = 'GC'
  ACTION = '!A'
  RATING = 'Ra'

  SECTION = 'SE' # indexhibit section
  WALT_WANDER = 'w'
  WALT_AUGMENT = 'a'
  WALT_LEARN = 'l'
  WALT_TOOLS = 't'

  TYPE_CHOICES = (
    (WALT_WANDER, 'WALT: WANDER'),
    (WALT_AUGMENT, 'WALT: AUGMENT'),
    (WALT_LEARN, 'WALT: LEARN'),
    (WALT_TOOLS, 'WALT: TOOLS'),
    (FREE, 'no category'),
    (AUTHOR, 'AUTHOR'),
    (KEYWORD, 'KEYWORD'),
    (INSTITUTION, 'Institution'),
    (RESEARCHER, 'Researcher'),
    (PLACE, 'Place'),
    (DATE, 'Date'),
    (GEOCOVER, 'Geographic coverage'),
    (ACTION, 'ACTION'),
    (RATING, 'RATING'),
    (SECTION, 'section code')
  )

  name = models.CharField(max_length=128) # e.g. 'Mr. E. Smith'
  slug = models.SlugField(max_length=128) # e.g. 'mr-e-smith'
  type = models.CharField(max_length=2, choices=TYPE_CHOICES, default=FREE) # e.g. 'author' or 'institution'

  # tag specification e.g. we want to specify an institution for a given author
  related = models.ManyToManyField('self', symmetrical=False, null=True, blank=True)


  def __unicode__(self):
    return "%s : %s"% (self.get_type_display(), self.name)

  class Meta:
    ordering = ["type", "slug" ]
    unique_together = ("type", "slug")

  def json(self):
    return{
      'id': self.id,
      'slug':self.slug,
      'name':self.name,
      'type':self.type,
      'type_label':self.get_type_display()
    }

class Document(models.Model):
  WAITING_FOR_PUBLICATION = 'W'
  PUBLIC 	= 'P' # make the document publicly available
  SHARED   = 'S' # editable only to authors, viewable by watchers
  DRAFT   = 'D'  # working draft, read and edit only to owner, shown as draft in your working platform
  PRIVATE = 'M' # read and edit only to owner


  STATUS_CHOICES = (
    (WAITING_FOR_PUBLICATION, 'publish it, please!'),
    (PUBLIC, 'public'),
    (SHARED, 'shared'), # allow watchers to view it, it remains private and it is not draft
    (DRAFT, 'draft'), # draft is viewable/editable by authors and owner only.
    (PRIVATE,'private'), # will not appears on drafts, but it is not published
 )

  LINK 	= 'B' # external link
  MEDIA   = 'I' # external iframe, image, audio or video
  TEXT   = 'T' # a note (at least originally)
  COMMENT  = 'C' # a cpomment,
  REFERENCE_COURSE = 'rO'
  REFERENCE_RESOURCE = 'rD'
  REFERENCE_RIGHTS = 'rR'
  REFERENCE_CONTROVERSY = 'rY'
  REFERENCE_CONTROVERSY_WEB = 'rW'
  REFERENCE_CONTROVERSY_VIDEO = 'rV'

  TYPE_CHOICES = (
    #( REFERENCE_COURSE, 'ref. course'),
    #( REFERENCE_RESOURCE, 'ref. resource'),
    #( REFERENCE_RIGHTS, 'ref. rights'),
    (REFERENCE_CONTROVERSY, 'ref. global controversy object'),
    (REFERENCE_CONTROVERSY_WEB, 'ref. controversy site'),
    (REFERENCE_CONTROVERSY_VIDEO, 'ref. controversy video'),
    (LINK,  'just a link'),
    (MEDIA, 'media'),
    (TEXT,  'text'), # notes and other stories
    (COMMENT, 'comment')
  )

  PDF = 'application/pdf'
  STORED_VIDEO = 'video/storedvideo'

  MIMETYPES_CHOICES = (
    (PDF, 'pdf'),
    (STORED_VIDEO, 'video - storage')
  )
  # storage function for filefield

  # the text content
  slug = models.SlugField(max_length=160, unique=True)
  title = models.CharField(max_length=160, default="")
  abstract = models.TextField(default="", blank=True, null=True)
  content = models.TextField(default="", blank=True, null=True)
  language =  models.CharField(max_length=2, default='en', choices=settings.LANGUAGES)
  mimetype = models.CharField(max_length=255, default="", choices=MIMETYPES_CHOICES, blank=True, null=True) # according to type, if needed (like imagefile)


  # TIME
  date = models.DateField(blank=True, null=True) # main date, manually added
  date_last_modified = models.DateTimeField(blank=True, null=True) #cfr save() method

  # URL LOCATION
  local = models.FileField(upload_to='documents/%Y-%m/',  blank=True, null=True) # local stored file inside media folder (aka upload)
  remote = models.TextField(blank=True, null=True) # local stored file inside storage folder. IT DOES NOT ALLOW UPLOAD! format: either http:/// or 

  permalink  = models.TextField(default="", blank=True, null=True) # remote link
  permalink_hash  = models.CharField(max_length=32, blank=True, null=True) # remote link

  # document friendship
  related = models.ManyToManyField("self", symmetrical=True, null=True, blank=True)
  parent  = models.ForeignKey("self", null=True, blank=True, related_name="children")
  status  = models.CharField(max_length=1, choices=STATUS_CHOICES, default=DRAFT, blank=True, null=True)
  type = models.CharField(max_length=2, choices=TYPE_CHOICES, default=TEXT)

  # tags and metadata. Reference is thre Reference Manager ID field (external resource then)
  tags = models.ManyToManyField(Tag, blank=True, null=True) # add tags !
  reference = models.CharField(max_length=60, default=0, blank=True, null=True)

  owner = models.ForeignKey(User) # the original owner
  authors = models.ManyToManyField(User, blank=True, null=True,  related_name="document_authored") # co-authors User.pin_authored
  watchers = models.ManyToManyField(User, blank=True, null=True, related_name="document_watched") # User.pin_watched

  def save(self, **kwargs):
    self.date_last_modified = datetime.utcnow().replace(tzinfo=utc)  
    #
    #  slug
    #  ----
    if not self.slug:
      max_length = 160 # associate it with slug field max length above
      slug = slugify(self.title)[:max_length] # safe autolimiting
      slug_base = slug
      i = 1;

      while self.__class__._default_manager.filter(slug=slug).count():
        candidate = '%s-%s' % (slug_base, i)

        if len(candidate) > max_length:
          slug = slug[:max_length-len('-%s' % i)]

        slug = re.sub('\-+','-',candidate)
        i += 1

      self.slug = slug

    super(Document, self).save()

  class Meta:
    unique_together = ("slug", "reference")
    ordering = ['-id']

  def __unicode__(self):
    return "%s (%s) a.k.a. %s" % (self.slug, self.language, self.title)

  # use this function if and only if the pin content is in bibtex (CLEAN) format
  def bib(self):
    return bibtex(self.content)

  def plaintext(self):
    return """
      |

  		%s
      ===

  			#%s %s
        language: %s
        mimetype: %s

  		___""" %(self.title, self.id, self.slug, self.language, self.mimetype)

  def get_attachments(self):
    attachments = []
    if self.remote is not None and len(self.remote):
      # pseudo Yaml
      filepaths = self.remote.strip(' \t\n\r').split('\n') # split multilines (i.e for video)
      
      for f in filepaths:
        # todo external file resolver e.g. if not http://
        parts = re.split('[/.]',f.strip('/'))
        attachments.append({
          'ext': parts[-1],
          'src': reverse('walt_storage', args=parts)
        })
    return attachments

  def get_organized_tags(self):
    tags = {}

    for t in self.tags.all():
      t_type = '%s'%t.get_type_display()
      if t_type not in tags:
        tags[t_type] = []
      tags[t_type].append(t)
    return tags
  
  def json(self, deep=False):
    # divide tags according to type
    tags = {}

    for t in self.tags.all():
      t_type = '%s'%t.get_type_display()
      if t_type not in tags:
        tags[t_type] = []
      tags[t_type].append(t.json())

    # undesratnd remote/ locales file
    attachments = self.get_attachments();

    
    return{
      'id': self.id,
      'slug':self.slug,
      'status': self.get_status_display(),
      'title': self.title,
      'abstract': self.abstract,
      'content': self.content,
      'language': self.language,
      'mimetype': self.mimetype,
      'permalink': self.permalink,
      'reference': self.reference,
      'owner': self.owner.username,
      'tags': tags,
      'type': self.type,
      'attachments':attachments,
      'date_last_modified': self.date_last_modified.isoformat() if self.date_last_modified is not None else None,
      'authors': [a.username for a in self.authors.all()]

    }