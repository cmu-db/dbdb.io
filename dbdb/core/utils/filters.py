# stdlib imports
import urllib.parse
from dataclasses import dataclass


# ==============================================
# FilterChoice
# ==============================================
@dataclass
class FilterChoice:
    id: str
    label: str
    # is_hidden: bool = False

# ==============================================
# FilterGroup
# ==============================================
@dataclass
class FilterGroup:
    id: str
    label: str
    choices: FilterChoice
    # has_more: bool = False

# ==============================================
# SearchBadge
# ==============================================
class SearchBadge:

    __slots__ = ['query','group_slug','group_name', 'badge_slug', 'badge_name']

    def __init__(self, query, group_slug, group_name, badge_slug, badge_name):
        self.query = query
        self.group_slug = group_slug
        self.group_name = group_name
        self.badge_slug = badge_slug
        self.badge_name = badge_name
        return

    def __repr__(self):
        return repr( tuple( map(str, (self.group_slug, self.group_name, self.badge_slug, self.badge_name)) ) )

    def get_removal_url(self):
        query = []

        for key,values in self.query.lists():
            for value in values:
                if key == self.group_slug and value == self.badge_slug:
                    continue
                query.append((key, value))

        return '?' + urllib.parse.urlencode(query, doseq=False)

    pass
