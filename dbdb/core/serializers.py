# stdlib imports
import datetime
# third-party imports
from rest_framework import serializers
# local imports
from .models import System
from .models import SystemVersion
#from .models import SystemMetadata

# ==============================================
# SystemSerializer
# ==============================================
class SystemSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = System
        fields = '__all__'
        #read_only_fields = '__all__'
        #fields = ['url', 'username', 'email', 'groups']
