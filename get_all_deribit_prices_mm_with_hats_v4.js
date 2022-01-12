const WebSocket = require('ws');
const fs = require('fs');
const { SSL_OP_SSLEAY_080_CLIENT_DH_BUG } = require('constants');
const { argv } = require('process');
const { timingSafeEqual } = require('crypto');
const { POINT_CONVERSION_HYBRID } = require('constants');
const moment = require('moment');
const fetch = require('node-fetch');
date_now_utc = () => {
    return new Date().toJSON().slice(0,19).toString();
    //return new Date().toJSON().replace('Z', '');
}

tgip = "http://localhost:8192";

var isWin = process.platform === "win32"

send_to_telegrambl4 = async(msg) => {
    let to_telegram = await fetch(tgip + '/eopt_info?message=' + msg)
    .then(res => res.json())
    .catch(err => console.log(err.message));

    return to_telegram;
}

command = () => {
    let first = ""
    let second = "";
    let arglst = [];
    for (let i = 2; i < argv.length; ++i)
        arglst.push(argv[i]);
    let args = arglst.join(' ');
    if (argv[0].includes('node.exe'))
        first = 'node';
    else
        first = argv[0];
    {
        let lst = argv[1].split('\\');
        if (lst.length > 1)
        {
            second = lst[lst.length - 1];
            
        }
        else
        {
            second = argv[1];
        }
    }
    return first + ' ' + second + ' ' + args;
}

fname = () =>
{
    let lst = argv[1].split('\\');
    return lst[lst.length - 1].split('.')[0];
}

let msg = "Your command for making table includes options deribit.com info: \n" + command() + '\n';
let logger = {log_file : fname() + ".log", log_err_file : fname()  + "_errors.log"};

print_in_log = (log, msg) =>
{
    try
    {
		if (isWin)
		{
			fs.appendFileSync("./" + logger[log], moment().format("YYYY-MM-DD HH:mm:ss") + ',-----------\n\n');
			fs.appendFileSync("./" + logger[log], msg + '\n');
			fs.appendFileSync("./" + logger[log], '\n');
		}
		else
		{
			fs.appendFileSync(logger[log], moment().format("YYYY-MM-DD HH:mm:ss") + ',-----------\n\n');
			fs.appendFileSync(logger[log], msg + '\n');
			fs.appendFileSync(logger[log], '\n');
		}
    }
    catch(e)
    {
        //send_to_telegrambl4(-5, "Error with writing information to log files\n" + e.message);
        console.log(e.message);
    }
    //logger[log] += msg + '\n';
}

date_now_new_york = () => {
    const timezone = "America/New_York";
    const usaTime = new Date().toLocaleString( "en-US", { timeZone: timezone});
    let arr = usaTime.split('/');
    let year_and_hours = arr[2].split(','); //year_and_hours[0] - year
    let hours = year_and_hours[1].split(":");
    if (hours[0] < 10)
        hours[0] = '0' + hours[0].slice(1);
    var time = year_and_hours[0] + '-' + arr[0] + '-' + arr[1] + ''+ hours[0] + ':' + hours[1];// + ':' + hours[2].slice(0,2);
    return time;
}

function timeConverter(timestamp){
    var a = new Date(timestamp);//.toLocaleString( "en-US", { timeZone: "America/New_York"});
    var months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    var year = a.getFullYear();
    //var month = months[a.getMonth()];
    //var day = a.getDay();
	//a = new Date(a);
    var month = a.getUTCMonth() + 1;
    var date = a.getUTCDate();
    var hour = a.getUTCHours();
    var min = a.getUTCMinutes();
    var sec = a.getUTCSeconds();

    if (month < 10)
        month = '0' + month;
    else
    if (date < 10)
        date = '0' + date;

    if (hour < 10)
        hour = '0' + hour;

    if (min < 10)
        min = '0' + min;


    if (sec < 10)
        sec = '0' + sec;

    var time = year + '-' + month + '-' + date + ' '+ hour + ':' + min + ':' + sec;
    //console.log(time);
    return time;
}

function time_to_timestamp(date) { 

    var a = new Date(date).toLocaleString( "en-US", { timeZone: "America/New_York"});
    //var a = new Date(date);
    //console.log(+new Date(a));
    return +new Date(a);
}

get_book_summary_by_instrument_with_params = (idxobj, currency) => {

    var msg = {
        "jsonrpc" : "2.0",
        "id" : 7617,
        "method" : "public/get_instruments",
        "params" : {
            "currency" : currency.split('-')[0],
            "kind" : "option",
            "expired" : false
        }
    };
    
    var msg_underline = {
        "jsonrpc": "2.0",
        "method": "public/get_index_price",
        "id": 42,
        "params": {
        "index_name": currency.split('-')[0].toLowerCase() + "_usd"}
    };

    var ws = new WebSocket('wss://www.deribit.com/ws/api/v2');

    let instrument_name; // имя опциона
    let mark_price; // рыночная
    let bid_price; // бид
    let ask_price; // аск
    let underline_price; // токен

    //let exp_timestamp = time_to_timestamp(expiration_time); // timestamp expiration
	//console.log(exp_timestamp);
    //массивы которые будут заполнены в ходе запросов, из которых будет напечатан результат
    let optionlst = [];
    let countlst = [];
    let bid_c = [];
    let bid_p = [];
    let ask_c = [];
    let ask_p = [];
    let mark_p = [];
    let mark_c = [];
    let strikes = [];
    let exp_time;
    ws.onerror = function (e) {
        send_to_telegrambl4("There is some problem with deribit.com. Error: \n" + e);
    }
   
    ws.onmessage = (e) => {
        //console.log("onmessage");
        let obj =  JSON.parse(e.data); // объект
        
        if (obj.id === 7617) // создание Set из опционов, которые которые удовлетворяют strike и expiration_time
        {
            if (obj.error != null) {
                console.log("Error: " + obj.error.message);
                //console.log("Reason: " + obj.error.data.reason + " with param: " + obj.error.data.param);
                return 0;
            }
            //console.log(exp_timestamp);
            for (let i = 0; i < obj.result.length; ++i) {

				/*console.log(lst.findIndex( elem => elem == obj.result[i].strike));
				console.log("elem: " + Math.ceil(obj.result[i].strike.toString()));
				console.log("arr: " + lst);*/
				//console.log(exp_timestamp);
				//console.log(obj.result[i]);
                //console.log(obj.result[i].expiration_timestamp);
                //27NOV20 ==
                if (obj.result[i].instrument_name.split('-')[1] == currency.split('-')[1]/* && lst.findIndex( elem => elem == obj.result[i].strike) != -1*/)
				{
                    optionlst.push(obj.result[i].instrument_name.slice(0,-1));
                    exp_time = obj.result[i].expiration_timestamp;
				}
            }
            
            let set = new Set(optionlst);

            optionlst = [...set].sort( (a, b) => {
                if (+a.split('-')[2] > +b.split('-')[2])
                    return 1;
                else if (+a.split('-')[2] < +b.split('-')[2])
                    return -1;
                else
                    return 0;
            });
            //console.log(optionlst);
            for (let i = 0; i < optionlst.length; ++i)
            {
                bid_c.push("");
                bid_p.push("");
                ask_c.push("");
                ask_p.push("");
                mark_c.push("");
                mark_p.push("");
                strikes.push("");

            }
            for (let i = 0; i < optionlst.length; ++i)
            {
                let arr = optionlst[i].split('-');
                strikes[i] = arr[arr.length - 2];
                //console.log(typeof(arr[arr.length - 2]));
            }
            var msgall = 
            {
                "jsonrpc" : "2.0",
                "id" : 9344,
                "method" : "public/get_book_summary_by_currency",
                "params" : {
                  "currency" : currency.split('-')[0],
                  "kind" : "option"
                }
            };

            if (!optionlst.length)
            {
                //console.log("There are no options with maturity " + currency.split('-')[1]);
                //console.log("Returned code 1");
                let err = "There are no options with maturity " + currency.split('-')[1] + '\nReturned code -1';
                print_in_log('log_err_file', err);
                idxobj.r_code = -1;
                idxobj.left.add(currency);
                //console.log("before: ", idxobj);
                ws.close();
                return -1;
            }
            else
                ws.send(JSON.stringify(msgall));

        } // end id 7617

        else if (obj.id === 9344) // информация по всем токенам, чтобы получить цены
        {

            if (obj.error != null) {
                console.log("Error: " + obj.error.message);
                //console.log("Reason: " + obj.error.data.reason + " with param: " + obj.error.data.param);
                ws.close();
                return -1;
            }
            else
            {
                for (let i = 0; i < obj.result.length; ++i) {

                    for (let j = 0; j < optionlst.length; ++j)
                    {
                        if (optionlst[j] + 'C' === obj.result[i].instrument_name)
                        {
                            //заполняем бид и аск для call
                            bid_c[j] = (obj.result[i].bid_price === null) ? "" : obj.result[i].bid_price;
                            ask_c[j] = (obj.result[i].ask_price === null) ? "" : obj.result[i].ask_price;
                            mark_c[j] = (obj.result[i].mark_price === null) ? "" : obj.result[i].mark_price;
                        }
                        else if (optionlst[j] + 'P' === obj.result[i].instrument_name)
                        {
                            //заполняем бид и аск для put
                            bid_p[j] = (obj.result[i].bid_price === null) ? "" : obj.result[i].bid_price;
                            ask_p[j] = (obj.result[i].ask_price === null) ? "" : obj.result[i].ask_price;
                            mark_p[j] = (obj.result[i].mark_price === null) ? "" : obj.result[i].mark_price;
                        }
                        
                    }

                } // end for throw obj.result
                var result = "";
                if (/*idxobj.idx == 0*/ idxobj.oldtime)
                    {
                        result = ",k,bid_c,ask_c,mark_c,bid_p,ask_p,mark_p,e,q,qty_p,qty_c,s0\n";
                        idxobj.oldtime = false;
                    }
				//debug
				//console.log(optionlst);
				/*console.log("ask_p");
				console.log(ask_p);
				
				console.log("bid_p");
				console.log(bid_p);
				
				console.log("bid_c");
				console.log(bid_c);
				
				console.log("ask_c");
				console.log(ask_c);
				*/

				//console.log(strikes);
				/*console.log(strikes);
				console.log(lst);*/
                // == "0" ? "" : (bid_c[j] * underline_price).toString()
                //let exec_time = date_now_utc().replace('T', ' ');
                for (let j = 0; j < optionlst.length; ++j) {
					
					//if (lst.findIndex(elem => elem == +strikes[j]) != -1)
					{
						bid_c[j] = bid_c[j] * underline_price == 0 ? "" : Math.round(bid_c[j] * underline_price * 10000) / 10000;
						ask_c[j] = ask_c[j] * underline_price == 0 ? "" : Math.round(ask_c[j] * underline_price * 10000) / 10000;
						bid_p[j] = bid_p[j] * underline_price == 0 ? "" : Math.round(bid_p[j] * underline_price * 10000) / 10000;
                        ask_p[j] = ask_p[j] * underline_price === 0 ? "" : Math.round(ask_p[j] * underline_price * 10000) / 10000;
                        
                        mark_c[j] = mark_c[j] * underline_price == 0 ? "" : Math.round(mark_c[j] * underline_price * 10000) / 10000;
                        mark_p[j] = mark_p[j] * underline_price === 0 ? "" : Math.round(mark_p[j] * underline_price * 10000) / 10000;
						let str = idxobj.idx + ',' + strikes[j].toString()
						+ ',' + bid_c[j]
                        + ',' + ask_c[j]
                        + ',' + mark_c[j]
						+ ',' + bid_p[j]
                        + ',' + ask_p[j]
                        + ',' + mark_p[j]
						+ ',' + timeConverter(exp_time).replace('T', ' ')
						+ ',' + idxobj.time
                        + ',' + "0" + "," + "0" + ',' +  underline_price.toString();
                        if (j != optionlst.length - 1)
                            str += '\n';
						result += str;
						++idxobj.idx;
					}
                }
                idxobj.r_code = 0;
                ws.close();
                console.log(result);
                return 0;
            }

        } // end id 9344

        else if (obj.id === 42) // если пришел запрос о цене underlying token
        {
            if (obj.error != null)
            {
                console.log("Error: " + obj.error.message);
                //console.log("Reason: " + obj.error.data.reason + " with param: " + obj.error.data.param);
                console.log("Returned code -32602");
                ws.close();
            }
            else
            {
                underline_price = obj.result.index_price;
                ws.send(JSON.stringify(msg));
            }

        } // end id 42
        /*else if (obj.id === 4000) // получение инструментов
        {
            if (obj.error != null)
            {
                console.log("Error: " + obj.error.message);
                console.log("Reason: " + obj.error.data.reason + " with param: " + obj.error.data.param);
                console.log("Returned code -32602");
                ws.close();
            }
            let arr = obj.result;
            console.log(arr);
            ws.close();
            
        }*/
    };
    ws.onopen = function () {
        //console.log("open");
        ws.on('error', function () {
            console.log("err");
        })
        ws.send(JSON.stringify(msg_underline));
    };
    
} // end get book

inames = [];
get_instruments = (u_token) => {
    var ws = new WebSocket('wss://www.deribit.com/ws/api/v2');
    var msg_intruments = {
        "jsonrpc" : "2.0",
        "id" : 4000,
        "method" : "public/get_instruments",
        "params" : {
            "currency" : u_token,
            "kind" : "option",
            "expired" : false
        }
    };
    ws.onerror = (e) => {
        send_to_telegrambl4("There is some problem with deribit.com. Error: \n" + e);
    }
    ws.onmessage = (e) => {
        //console.log("onmessage");
        let obj =  JSON.parse(e.data); // объект
        let i_names = new Set();
        if (obj.id === 4000) // создание Set из опционов, которые которые удовлетворяют strike и expiration_time
        {
            let arr = obj.result;
            //console.log(arr);
            for (let i = 0 ; i < arr.length; ++i)
            {
                let spl = arr[i].instrument_name.split('-');
                spl.splice(2);
                
                i_names.add(spl.join('-'));
            }
            let arrin = [...i_names];

            fs.writeFileSync('./inames.txt', arrin.toString());
            //console.log("deb");
            ws.close();
        }
    }
    
    ws.onopen = function () {
        //console.log("open");
        ws.send(JSON.stringify(msg_intruments));
    }
}


get_deribit_prices_mm = () => {

    /*if (process.argv.length < 3)
    {

        console.log("Not enough arguments. Minimus is 3")
        console.log("usage: node get_deribit_prices_mm.js <u_token-DATE> <strike1>, ...");
        return;
    }

    let currency = process.argv[2];
    const exec_book = () => {

        get_book_summary_by_instrument_with_params(currency);
    }
    exec_book();*/

    if (process.argv.length < 4)
    {

        console.log("Not enough arguments. Required 1")
        console.log("usage: node get_all_deribit_prices_mm.js <period in sec (0: without timer)> <u_token>");
        return;
    }
    if (isNaN(+process.argv[2]))
    {
        console.log("Incorrect period parameter or missed");
        return;
    }
    let period = process.argv[2] - 5;
    let u_token = process.argv[3];

    let idxobj = {idx: 0, oldtime: true, r_code: 0, left: new Set([]), time: 0};
    //console.log(inames);
    const exec = async () => {
        let timer;
        //console.log("left: ", left_inames);
        //console.log("inames: ", inames);
        get_instruments(u_token);
        await new Promise(res => setTimeout(res, 5000));
        idxobj.time = date_now_utc().replace('T', ' ');
        let inames;
        try {
            inames = fs.readFileSync('./inames.txt').toString().split(',');
            fs.unlinkSync('./inames.txt');

            for (let i = 0; i < inames.length; ++i)
            {
                if (idxobj.left.has(inames[i]) == true)
                    {
                        if (idxobj.left.size == inames.length)
                            {
                                print_in_log('log_file', "All options expired. Returned code: 0");
                                clearTimeout(timer);
                                return 0;
                            }
                        continue;
                    }

                get_book_summary_by_instrument_with_params(idxobj, inames[i]);
                idxobj.oldtime = true;
                //console.log("after: ", idxobj);
                /*if (idxobj.r_code < 0 && +new Date() > +new Date(inames[i].split('-')[1]) ) 
                {
                    left_inames.push(inames[i]);
                }*/
            }
        }
        catch(err)
        {
            print_in_log('log_err_file', err.message);
        }
        //console.log(inames);
        
    if (period != -5)
        timer = setTimeout(exec, period * 1000);
    }
    exec();
}

/*debug time*/
//console.log(date_now_utc());
//console.log(date_now_new_york());
//console.log(time_to_timestamp('2021-06-25T04:00:00'));
//console.log(timeConverter(1624608000000));
print_in_log('log_file', msg);
get_deribit_prices_mm();
