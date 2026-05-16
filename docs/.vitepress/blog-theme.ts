import { getThemeConfig } from '@sugarat/theme/node';

// All configuration options, see documentation: https://theme.sugarat.top/
const blogTheme = getThemeConfig({
  locales: {
    fr: {
      formatShowDate: (date: string | Date) => {
        const d = new Date(date);
        const diff = Date.now() - d.getTime();
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (minutes < 1) return "À l'instant";
        if (hours < 1 && minutes > 1) return `il y a ${minutes}mins`;
        if (hours < 1) return `il y a ${minutes}min`;
        if (days < 1) return `il y a ${hours}h`;
        if (days < 7) return `il y a ${days}j`;
        return d.toLocaleDateString('fr-FR');
      },
      article: {
        analyzeTitles: {
          topReadTime: '{{value}} min de lecture',
          inlineWordCount: '{{value}} mots',
          inlineReadTime: '{{value}} min',
          topWordCount: '{{value}} mots',
          readTime: 'Temps de lecture',
          lastUpdated: 'Mis à jour le',
          wordCount: 'Nombre de mots',
          publishDate: 'Publié le',
          author: 'Auteur',
          tag: 'Tags'
        }
      },

      recommend: {
        title: 'Voir aussi'
      }
    },

    root: {
      formatShowDate: (date: string | Date) => {
        const d = new Date(date);
        const diff = Date.now() - d.getTime();
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (minutes < 1) return 'Just now';
        if (hours < 1 && minutes > 1) return `${minutes}mins ago`;
        if (hours < 1) return `${minutes}min ago`;
        if (days < 1) return `${hours}h ago`;
        if (days < 7) return `${days}d ago`;
        return d.toLocaleDateString('en');
      },
      article: {
        analyzeTitles: {
          inlineWordCount: '{{value}} words',
          topReadTime: '{{value}} min read',
          topWordCount: '{{value}} words',
          inlineReadTime: '{{value}} min',
          lastUpdated: 'Last updated',
          readTime: 'Reading time',
          publishDate: 'Published',
          wordCount: 'Word count',
          author: 'Author',
          tag: 'Tags'
        }
      },
      recommend: {
        title: 'Related articles'
      }
    }
  },

  search: {
    locales: {
      fr: {
        heading: 'Total : {{searchResult}}',
        placeholder: 'Rechercher...',
        btnPlaceholder: 'Rechercher',
        emptyText: 'Aucun résultat',
        toNavigate: 'naviguer',
        toSelect: 'confirmer',
        toClose: 'fermer',
        searchBy: ' '
      },
      root: {
        heading: 'Total: {{searchResult}}',
        placeholder: 'Search...',
        btnPlaceholder: 'Search',
        emptyText: 'No results'
      }
    },
    excludeSelector: ['code span.line', 'span.lang', '.good-work-mojo-msg', '.inspiring-quote', '.inspiring-quote-author']
  },

  footer: {
    copyright: 'MIT License | Игорь Казанова (Igor Casanova)'
  },

  author: 'Игорь Казанова',

  darkTransition: false,

  themeColor: 'el-blue',

  hotArticle: false
});

export { blogTheme };
