from .api import CounterView, organization_autocomplete, system_autocomplete
from .auth import CreateUserView, SetupUserView
from .browse import BrowseView
from .home import HomeView
from .misc import EmptyFieldsView, SitemapView
from .stats import StatsView
from .system import (
    RecentChangesView,
    SystemEditView,
    SystemRevisionList,
    SystemRevisionView,
    SystemView,
)