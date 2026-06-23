document.addEventListener('DOMContentLoaded', () => {
  // 1. Sticky Navigation Scrolled State
  const header = document.querySelector('header');
  const handleScroll = () => {
    if (header) {
      if (window.scrollY > 20) {
        header.classList.add('scrolled');
      } else {
        header.classList.remove('scrolled');
      }
    }
  };
  window.addEventListener('scroll', handleScroll);
  handleScroll(); // Initial run in case of reload in the middle of page

  // 2. Accessible Mobile Nav Hamburger Menu
  const navToggle = document.querySelector('.nav-toggle');
  const navMenu = document.querySelector('.nav-menu');
  
  if (navToggle && navMenu) {
    const toggleMenu = (open) => {
      const isExpanded = open !== undefined ? open : navToggle.getAttribute('aria-expanded') === 'true';
      const nextState = !isExpanded;
      navToggle.setAttribute('aria-expanded', String(nextState));
      navMenu.classList.toggle('active', nextState);
      navToggle.classList.toggle('active', nextState);
      document.body.classList.toggle('nav-open', nextState);
    };

    navToggle.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleMenu();
    });

    // Close menu when clicking a link
    const navLinks = navMenu.querySelectorAll('a');
    navLinks.forEach(link => {
      link.addEventListener('click', () => {
        toggleMenu(false);
      });
    });

    // Close menu on Escape key press
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && navMenu.classList.contains('active')) {
        toggleMenu(false);
        navToggle.focus();
      }
    });

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
      if (navMenu.classList.contains('active') && !navMenu.contains(e.target) && !navToggle.contains(e.target)) {
        toggleMenu(false);
      }
    });
  }

  // 3. Scroll Reveal Animations (prefers-reduced-motion respect)
  const revealElements = document.querySelectorAll('.reveal');
  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)');

  if (revealElements.length > 0) {
    if (prefersReduced.matches) {
      // Respect user motion preference: show all immediately
      revealElements.forEach(el => el.classList.add('is-visible'));
    } else {
      const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.15
      };

      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            // Unobserve once shown
            observer.unobserve(entry.target);
          }
        });
      }, observerOptions);

      revealElements.forEach(el => observer.observe(el));
    }
  }

  // 4. Code Block Copy to Clipboard Utility
  const copyButtons = document.querySelectorAll('.copy-btn');
  copyButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const codeEl = btn.previousElementSibling || btn.parentElement.querySelector('code');
      if (codeEl) {
        const textToCopy = codeEl.textContent.trim();
        navigator.clipboard.writeText(textToCopy).then(() => {
          const originalText = btn.textContent;
          btn.textContent = 'Copied!';
          btn.classList.add('copied');
          btn.setAttribute('aria-label', 'Copied to clipboard');
          setTimeout(() => {
            btn.textContent = originalText;
            btn.classList.remove('copied');
            btn.setAttribute('aria-label', 'Copy code snippet');
          }, 2000);
        }).catch(err => {
          console.error('Failed to copy code to clipboard: ', err);
        });
      }
    });
  });
});
