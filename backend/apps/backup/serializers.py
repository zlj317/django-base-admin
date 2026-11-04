"""数据备份模块序列化器。"""
from rest_framework import serializers

from apps.backup.models import BackupRecord, BackupStrategy


class BackupRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupRecord
        fields = '__all__'


class BackupStrategySerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupStrategy
        fields = '__all__'
