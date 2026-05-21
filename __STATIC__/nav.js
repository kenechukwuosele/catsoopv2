// CU Quiz App - Global Navigation Injector
document.addEventListener('DOMContentLoaded', function() {
  // --- Helper: get current page path parts ---
  const path = window.location.pathname.replace(/\/$/, '');
  const parts = path.split('/').filter(Boolean);
  const baseUrl = window.location.origin;

  // --- Detect username from page (CatSooP puts it in the DOM) ---
  function getUsername() {
    const el = document.querySelector('.cs-username, #cs_username, [data-username]');
    if (el) return el.textContent.trim();
    const loginLink = document.querySelector('a[href*="login"]');
    if (loginLink) return null;
    return null;
  }

  // --- Build breadcrumb trail ---
  function buildBreadcrumb() {
    let trail = '<a href="/">&#127968; Home</a>';
    let url = '';
    parts.forEach((part, i) => {
      url += '/' + part;
      const label = part.charAt(0).toUpperCase() + part.slice(1).replace(/_/g, ' ');
      if (i === parts.length - 1) {
        trail += ' <span class="sep">›</span> <span class="current">' + label + '</span>';
      } else {
        trail += ' <span class="sep">›</span> <a href="' + url + '">' + label + '</a>';
      }
    });
    return trail;
  }

  // --- Inject Navbar ---
  const username = getUsername();
  const authBtn = username
    ? '<span class="nav-username">&#128100; ' + username + '</span><a class="nav-auth-btn" href="/logout">Logout</a>'
    : '<a class="nav-auth-btn" href="/login">Login</a>';

  const navbar = document.createElement('div');
  navbar.id = 'cu-navbar';
  navbar.innerHTML = `
    <div class="nav-left">
      <button class="sidebar-toggle" id="cu-sidebar-btn" title="Menu">&#9776;</button>
      <a class="nav-brand" href="/">CU Quiz App</a>
      <a class="nav-home-btn" href="/">&#8962; Home</a>
    </div>
    <div class="nav-right">
      ${authBtn}
    </div>
  `;
  document.body.prepend(navbar);

  // --- Inject Breadcrumb + Back Button ---
  const breadcrumb = document.createElement('div');
  breadcrumb.id = 'cu-breadcrumb';
  breadcrumb.innerHTML = `
    <a id="cu-back-btn" href="javascript:history.back()">&#8592; Back</a>
    <div id="cu-breadcrumb-trail">${buildBreadcrumb()}</div>
  `;
  navbar.insertAdjacentElement('afterend', breadcrumb);

  // --- Inject Sidebar ---
  const sidebar = document.createElement('div');
  sidebar.id = 'cu-sidebar';
  sidebar.innerHTML = `
    <div class="sidebar-section">Navigation</div>
    <ul>
      <li><a href="/">&#127968; Home</a></li>
    </ul>
    <div class="sidebar-section">Courses</div>
    <ul>
      <li><a href="/Physics" ${parts[0]==='Physics'?'class="active"':''}>&#9883; Physics</a></li>
      <li><a href="/Programming" ${parts[0]==='Programming'?'class="active"':''}>&#128187; Programming</a></li>
      <li><a href="/Sports" ${parts[0]==='Sports'?'class="active"':''}>&#127942; Sports</a></li>
    </ul>
    <div class="sidebar-section">Account</div>
    <ul>
      ${username
        ? '<li><a href="/logout">&#128682; Logout</a></li>'
        : '<li><a href="/login">&#128274; Login</a></li><li><a href="/register">&#128221; Register</a></li>'
      }
    </ul>
  `;
  document.body.appendChild(sidebar);

  // --- Inject Overlay ---
  const overlay = document.createElement('div');
  overlay.id = 'cu-sidebar-overlay';
  document.body.appendChild(overlay);

  // --- Sidebar Toggle Logic ---
  document.getElementById('cu-sidebar-btn').addEventListener('click', function() {
    sidebar.classList.toggle('open');
    overlay.classList.toggle('show');
  });

  overlay.addEventListener('click', function() {
    sidebar.classList.remove('open');
    overlay.classList.remove('show');
  });

  // --- Hide back button on homepage ---
  if (parts.length === 0) {
    document.getElementById('cu-back-btn').style.display = 'none';
  }

});
