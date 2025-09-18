document.addEventListener('DOMContentLoaded', function(){
  // Theme toggle (persist in localStorage)
  const themeBtn = document.getElementById('themeToggle');
  const root = document.documentElement;
  const saved = localStorage.getItem('site-theme') || 'light';
  document.documentElement.setAttribute('data-theme', saved);
  if(themeBtn) themeBtn.textContent = saved === 'dark' ? 'Light' : 'Dark';
  themeBtn && themeBtn.addEventListener('click', () => {
    const cur = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
    const next = cur === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('site-theme', next);
    themeBtn.textContent = next === 'dark' ? 'Light' : 'Dark';
  });

  // Simple hero animation interaction
  const hero = document.getElementById('heroSVG');
  if(hero){
    const plane = hero.querySelector('#plane');
    const city = hero.querySelector('#city');
    let flying = false;
    hero.addEventListener('mouseenter', ()=> {
      if(flying) return;
      flying = true;
      plane.animate([
        { transform: 'translate(-60px,160px) rotate(-10deg)' },
        { transform: 'translate(120px,40px) rotate(-20deg)' },
        { transform: 'translate(260px,-40px) rotate(-30deg)' }
      ], { duration: 1200, easing: 'cubic-bezier(.2,.8,.2,1)', fill: 'forwards' }).onfinish = () => {
        flying = false;
      };
    });
    // Click city -> redirect to search for Jamshedpur
    city && city.addEventListener('click', ()=> {
      window.location = '/search?q=Jamshedpur';
    });
  }

  // Favorites button on post page
  const favBtn = document.getElementById('favBtn');
  if(favBtn){
    const articleUrl = window.location.href;
    const favs = JSON.parse(localStorage.getItem('favorites') || '[]');
    function updateBtn(){
      const exists = favs.find(f => f.url === articleUrl);
      favBtn.textContent = exists ? 'Saved' : 'Save to favorites';
      favBtn.disabled = !!exists;
    }
    updateBtn();
    favBtn.addEventListener('click', ()=> {
      const title = document.querySelector('h2') ? document.querySelector('h2').innerText : document.title;
      favs.push({title, url: articleUrl, savedAt: Date.now()});
      localStorage.setItem('favorites', JSON.stringify(favs));
      updateBtn();
    });
  }

});
