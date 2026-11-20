(() => {
  const ID = '1Aj567BDeYxuWxenTX61aLLNjKRp_1ljcAYDZCl1_vsg';
  const fmt = 'pptx';   // đổi thành 'pptx' nếu muốn bản PowerPoint

  const a = document.createElement('a');
  a.href = `https://docs.google.com/presentation/d/${ID}/export/${fmt}`;
  document.body.appendChild(a);
  a.click();
  a.remove();

  console.log('✅ Đã gửi yêu cầu tải');
})();
