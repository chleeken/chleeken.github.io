// 广告内容配置
const ads = {
    leftAd: '<div><!-- 广告内容 --><a href="https://chleeken.github.io/" target="_blank">chleeken的page主页</a></div>',
    topRightAd: '<div><!-- 广告内容 --><a href="https://chleeken.github.io/myurls.html" target="_blank">我的导航</a></div>'
};

// 加载广告
function loadAds() {
    document.getElementById('leftAd').innerHTML = ads.leftAd;
    document.getElementById('topRightAd').innerHTML = ads.topRightAd;
}

// 更新侧边栏位置
function updateSidebarPosition() {
    const leftSidebar = document.querySelector('.left-sidebar');
    const rightSidebar = document.querySelector('.right-sidebar');
    const mainContent = document.querySelector('.main-content');

    if (leftSidebar && mainContent) {
        const mainLeft = mainContent.offsetLeft;
        leftSidebar.style.left = (mainLeft - 205) + 'px';
    }

    if (rightSidebar && mainContent) {
        const mainRight = mainContent.offsetLeft + mainContent.offsetWidth;
        rightSidebar.style.right = 'auto';
        rightSidebar.style.left = (mainRight + 5) + 'px';
    }
}

// 页面加载完成后执行
window.addEventListener('load', () => {
    loadAds();
    updateSidebarPosition();
});

// 窗口调整时更新侧边栏位置
window.addEventListener('resize', updateSidebarPosition);