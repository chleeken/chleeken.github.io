// 广告内容配置
const ads = {
    leftAd: '<div><!-- 广告内容 --><a href="https://chleeken.github.io/" target="_blank">靳好宝博客</a></div>',
    topRightAd: '<div><!-- 广告内容 --><a href="https://chleeken.github.io/myurls.html" target="_blank">我的导航</a></div>'
};

// 加载广告
function loadAds() {
    document.getElementById('leftAd').innerHTML = ads.leftAd;
    document.getElementById('topRightAd').innerHTML = ads.topRightAd;
}

// 动态计算侧边栏位置：跟随主内容，保持0.1%间隙
function updateSidebarPosition() {
    const mainContent = document.querySelector('.main-content');
    const leftSidebar = document.getElementById('leftAd');
    const rightSidebar = document.querySelector('.right-sidebar');

    if (!mainContent || !leftSidebar || !rightSidebar) return;

    const vw = window.innerWidth;
    const gap = vw * 0.001;

    // 左侧栏：右侧边框距主内容左边缘0.1%
    const mainRect = mainContent.getBoundingClientRect();
    leftSidebar.style.top = '50%';
    leftSidebar.style.transform = 'translateY(-50%)';
    leftSidebar.style.left = (mainRect.left - leftSidebar.offsetWidth - gap) + 'px';

    // 右侧栏：左侧边框距主内容右边缘0.1%
    const rsWidth = rightSidebar.offsetWidth;
    rightSidebar.style.top = '50%';
    rightSidebar.style.transform = 'translateY(-50%)';
    rightSidebar.style.left = (mainRect.right + gap) + 'px';
}

// 页面加载完成后执行
window.addEventListener('load', function() {
    loadAds();
    updateSidebarPosition();
});

// 窗口resize时重新计算位置
window.addEventListener('resize', updateSidebarPosition);









