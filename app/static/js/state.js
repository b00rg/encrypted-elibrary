export const state = {
  user: null,
  view: 'loading', // 'loading' | 'auth' | 'shelf' | 'pending' | 'admin' | 'shelves'
  shelfBooks: [],
  searchResults: [],
  searchQuery: '',
  searchLoading: false,
  adminUsers: [],
  loadingShelf: false,
  readLaterFilter: false,
  // Group shelves
  myShelves: [],
  activeShelfId: null,
  activeShelfBooks: [],
  loadingShelfBooks: false,
  // Review display
  showEncryptedReviews: false,
  readLaterReviews: {},        // { work_id: [{shelf_id, shelf_name, book_id, reviews:[]}] }
  loadingReadLaterReviews: false,
};
