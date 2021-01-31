#!/usr/bin/env python3
# Convenience function during debugging stage
from karmamarket import Marketplace
mp = Marketplace()
mp._delete_data()
mp._create_new_marketplace()
mp._create_initial_data()
