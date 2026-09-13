import re
import uuid
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.organizations.models import Organization


ALLOWED_VIDEO_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "bilibili.com",
    "www.bilibili.com",
    "m.bilibili.com",
    "player.bilibili.com",
    "b23.tv",
}


def validate_video_url(value):
    if not value:
        return

    host = (urlparse(value).hostname or "").lower()

    if host not in ALLOWED_VIDEO_HOSTS:
        raise ValidationError(
            "A mídia deve ser um link do YouTube ou Bilibili."
        )


def youtube_video_id(url):
    if not url:
        return ""

    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    if host == "youtu.be":
        return parsed.path.strip("/").split("/")[0]

    if "youtube.com" in host:
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [""])[0]

        for prefix in ("/shorts/", "/embed/"):
            if parsed.path.startswith(prefix):
                return parsed.path[len(prefix):].split("/")[0]

    return ""


class Exercise(models.Model):

    class PublicationStatus(models.TextChoices):
        PRIVATE = "private", "Privado"
        PENDING = "pending", "Aguardando aprovação"
        APPROVED = "approved", "Aprovado"
        REJECTED = "rejected", "Rejeitado"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="exercises",
    )

    # Exercício global usado como base para uma personalização.
    base_exercise = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="personalizations",
    )

    # Exercício privado que originou uma publicação global.
    published_from = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="published_versions",
    )

    source_id = models.CharField(
        max_length=160,
        unique=True,
        null=True,
        blank=True,
    )

    name = models.CharField("Nome", max_length=160)
    description = models.TextField("Descrição", blank=True)

    primary_muscle = models.CharField(
        "Músculo principal",
        max_length=120,
    )

    secondary_muscles = models.CharField(
        "Músculos secundários",
        max_length=250,
        blank=True,
    )

    equipment = models.CharField(
        "Equipamento",
        max_length=120,
        blank=True,
    )

    body_part = models.CharField(
        "Região corporal",
        max_length=120,
        blank=True,
    )

    category = models.CharField(
        "Categoria",
        max_length=80,
        blank=True,
    )

    difficulty = models.CharField(
        "Dificuldade",
        max_length=80,
        blank=True,
    )

    met = models.FloatField(null=True, blank=True)
    is_unilateral = models.BooleanField(default=False)
    is_bodyweight = models.BooleanField(default=False)

    instructions = models.TextField(
        "Instruções",
        blank=True,
    )

    # Somente YouTube/Bilibili.
    media_url = models.URLField(
        "Vídeo YouTube/Bilibili",
        blank=True,
        validators=[validate_video_url],
    )

    # Imagens originais RepDB.
    image_start_url = models.URLField(
        max_length=500,
        blank=True,
    )
    image_peak_url = models.URLField(
        max_length=500,
        blank=True,
    )
    image_main_url = models.URLField(
        max_length=500,
        blank=True,
    )

    # PT-BR.
    name_ptbr = models.CharField(
        max_length=160,
        blank=True,
    )
    primary_muscle_ptbr = models.CharField(
        max_length=120,
        blank=True,
    )
    secondary_muscles_ptbr = models.CharField(
        max_length=250,
        blank=True,
    )
    equipment_ptbr = models.CharField(
        max_length=120,
        blank=True,
    )
    category_ptbr = models.CharField(
        max_length=80,
        blank=True,
    )
    difficulty_ptbr = models.CharField(
        max_length=80,
        blank=True,
    )
    instructions_ptbr = models.TextField(blank=True)

    publication_status = models.CharField(
        max_length=20,
        choices=PublicationStatus.choices,
        default=PublicationStatus.PRIVATE,
    )

    publication_requested_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    publication_reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    publication_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_exercises",
    )

    publication_rejection_reason = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    @property
    def is_global(self):
        return self.organization_id is None

    @property
    def display_name(self):
        return self.name_ptbr or self.name

    @property
    def display_primary_muscle(self):
        return self.primary_muscle_ptbr or self.primary_muscle

    @property
    def display_equipment(self):
        return self.equipment_ptbr or self.equipment

    @property
    def display_difficulty(self):
        return self.difficulty_ptbr or self.difficulty

    @property
    def display_instructions(self):
        return self.instructions_ptbr or self.instructions

    @property
    def repdb_image_url(self):
        return (
            self.image_start_url
            or self.image_main_url
            or self.image_peak_url
            or (
                self.base_exercise.repdb_image_url
                if self.base_exercise
                else ""
            )
        )

    @property
    def youtube_thumbnail_url(self):
        video_id = youtube_video_id(self.media_url)

        if video_id:
            return (
                f"https://img.youtube.com/vi/"
                f"{video_id}/hqdefault.jpg"
            )

        return ""

    @property
    def display_image_url(self):
        return self.youtube_thumbnail_url or self.repdb_image_url

    @property
    def media_provider(self):
        if not self.media_url:
            return ""

        host = (
            urlparse(self.media_url).hostname or ""
        ).lower()

        if "youtu" in host:
            return "YouTube"

        return "Bilibili"

    def request_publication(self):
        if self.is_global:
            return

        self.publication_status = self.PublicationStatus.PENDING
        self.publication_requested_at = timezone.now()
        self.publication_reviewed_at = None
        self.publication_reviewed_by = None
        self.publication_rejection_reason = ""

        self.save(
            update_fields=[
                "publication_status",
                "publication_requested_at",
                "publication_reviewed_at",
                "publication_reviewed_by",
                "publication_rejection_reason",
                "updated_at",
            ]
        )

    def publish_as_global(self, admin_user):
        if self.is_global:
            return self

        source_id = f"community:{self.pk}"

        global_exercise, _ = Exercise.objects.get_or_create(
            source_id=source_id,
            defaults={
                "organization": None,
                "name": self.name,
                "primary_muscle": self.primary_muscle,
            },
        )

        fields = [
            "name",
            "description",
            "primary_muscle",
            "secondary_muscles",
            "equipment",
            "body_part",
            "category",
            "difficulty",
            "met",
            "is_unilateral",
            "is_bodyweight",
            "instructions",
            "media_url",
            "image_start_url",
            "image_peak_url",
            "image_main_url",
            "name_ptbr",
            "primary_muscle_ptbr",
            "secondary_muscles_ptbr",
            "equipment_ptbr",
            "category_ptbr",
            "difficulty_ptbr",
            "instructions_ptbr",
        ]

        for field in fields:
            setattr(
                global_exercise,
                field,
                getattr(self, field),
            )

        # Herda imagens da base RepDB se necessário.
        if self.base_exercise:
            for field in (
                "image_start_url",
                "image_peak_url",
                "image_main_url",
            ):
                if not getattr(global_exercise, field):
                    setattr(
                        global_exercise,
                        field,
                        getattr(self.base_exercise, field),
                    )

        global_exercise.organization = None
        global_exercise.published_from = self
        global_exercise.publication_status = (
            self.PublicationStatus.APPROVED
        )
        global_exercise.save()

        self.publication_status = self.PublicationStatus.APPROVED
        self.publication_reviewed_at = timezone.now()
        self.publication_reviewed_by = admin_user
        self.publication_rejection_reason = ""

        self.save(
            update_fields=[
                "publication_status",
                "publication_reviewed_at",
                "publication_reviewed_by",
                "publication_rejection_reason",
                "updated_at",
            ]
        )

        return global_exercise


    @property
    def embed_video_url(self):
        if not self.media_url:
            return ""

        parsed = urlparse(self.media_url)
        host = (parsed.hostname or "").lower()

        if "youtube.com" in host or host == "youtu.be":
            video_id = youtube_video_id(self.media_url)

            if video_id:
                return (
                    "https://www.youtube.com/embed/"
                    f"{video_id}"
                    "?playsinline=1&rel=0"
                )

        if "bilibili.com" in host:
            match = re.search(
                r"/video/(BV[a-zA-Z0-9]+)",
                parsed.path,
            )

            if match:
                return (
                    "https://player.bilibili.com/"
                    "player.html?"
                    f"bvid={match.group(1)}"
                    "&autoplay=0"
                )

        return ""

    def __str__(self):
        return self.display_name
