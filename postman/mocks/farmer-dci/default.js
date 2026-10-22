// Fault shapes derive from the DCI search envelope used by Registry.
const http = require('http');
http.createServer(async (req, res) => {
  const mode = req.url.split('?')[0].split('/').filter(Boolean).pop();
  if (req.method !== 'POST') { res.writeHead(501); return res.end(); }
  if (mode === 'timeout') await new Promise(resolve => setTimeout(resolve, 1000));
  if (mode === 'html') { res.writeHead(502, {'Content-Type':'text/html'}); return res.end('<html>proxy unavailable</html>'); }
  res.setHeader('Content-Type','application/json');
  if (['unauthorized','rate-limit','server-error'].includes(mode)) {
    res.statusCode = {'unauthorized':401,'rate-limit':429,'server-error':503}[mode];
    return res.end(JSON.stringify({error:mode}));
  }
  if (mode === 'array') return res.end('[]');
  if (mode === 'invalid-json') return res.end('{');
  const personal = {member_identifier:[{identifier_type:'UIN',identifier_value:'9999102220260001'}],
    demographic_info:{name:{given_name:'Synthetic',second_name:'Lookup',surname:'Fixture'},sex:'male',birth_date:'1990-01-01',phone_number:['+251911111111']}};
  if (mode === 'wrong-identity') personal.member_identifier[0].identifier_value = '9999102220260002';
  if (mode === 'missing-identifier') delete personal.member_identifier;
  let records = [{farmer_personal_details:personal}];
  if (mode === 'zero') records = [];
  if (mode === 'multiple') records = [records[0],records[0]];
  if (mode === 'no-scope') records = [{}];
  if (mode === 'scalar-record') records = ['bad'];
  const item = {status:mode === 'rejected' ? 'rjct':'succ',data:{reg_records:records}};
  const body = {header:{status:mode === 'header-rejected'?'rjct':'succ'},message:{search_response:[item]}};
  if (mode === 'multiple-responses') body.message.search_response.push(item);
  if (mode === 'no-message') delete body.message;
  if (mode === 'scalar-message') body.message = 'bad';
  res.end(JSON.stringify(body));
}).listen(process.env.PORT || 49181);
