from rest_framework import serializers
from .models import Project, AuditEvent

class ProjectSerializer(serializers.ModelSerializer):
    assets_count = serializers.IntegerField(source='model_assets.count', read_only=True)

    class Meta:
        model = Project
        fields = ['id', 'name', 'slug', 'description', 'created_at', 'updated_at', 'is_active', 'assets_count']
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at', 'assets_count']

    def create(self, validated_data):
        from django.utils.text import slugify
        import uuid
        name = validated_data['name']
        base_slug = slugify(name) or 'project'
        slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
        
        # Asignar usuario dueño por defecto si no está autenticado
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        if not user:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user, _ = User.objects.get_or_create(username='default_operator', defaults={'email': 'operator@industrial3d.local'})
            
        validated_data['slug'] = slug
        validated_data['owner'] = user
        return super().create(validated_data)

class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = '__all__'
