export const state = {
  user: null,
  view: 'loading', // 'loading' | 'auth' | 'shelf' | 'pending' | 'admin'
  shelfBooks: [],
  searchResults: [],
  searchQuery: '',
  searchLoading: false,
  adminUsers: [],
  loadingShelf: false,
  readLaterFilter: false,
};
