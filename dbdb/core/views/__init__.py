from .api import CounterView, organization_autocomplete, system_autocomplete
from .auth import CreateUserView, SetupUserView, SignupRequestView, SignupPendingView, ProfileView
from .browse import BrowseView
from .home import HomeView
from .misc import EmptyFieldsView, SitemapView
from .organization import OrganizationView
from .stats import StatsView
from .system import (
    RecentChangesView,
    SystemEditView,
    SystemVersionDiffView,
    SystemView,
)
