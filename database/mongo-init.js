db = db.getSiblingDB('smartfeed');

db.createCollection('news_posts');
db.news_posts.createIndex({ rss_id: 1 }, { unique: true });
