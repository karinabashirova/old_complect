//v002
import fs from 'fs';
import { Option } from './utils/opt_utils.js';
import Web3 from 'web3';
import moment from 'moment';

const conf = JSON.parse(fs.readFileSync('./config/config.cfg').toString());
const web3 = new Web3(conf.net.httpProvider);
const f_in = './active_options.csv';
const f_out = './ob_make_orders.csv';
const f_log = './get_ob_make_orders.log';

async function main() {
    let opts = fs.readFileSync(f_in).toString().split('\n');
    let eopt = new web3.eth.Contract(JSON.parse(fs.readFileSync('./config/abi/EOpt.abi').toString()), conf.EOpt.adr);
    for (let i = 0; i < opts.length - 1; i++) {
        let params = opts[i].split(',');
        let raw_f_tok = params[0];
        let raw_u_tok = params[1];
        let raw_isCall = params[2];
        let raw_maturity = params[4];
        let f_tok = new web3.eth.Contract(JSON.parse(fs.readFileSync('./config/abi/ETok.abi').toString()), conf.tokens[raw_f_tok]);
        let u_tok = new web3.eth.Contract(JSON.parse(fs.readFileSync('./config/abi/ETok.abi').toString()), conf.tokens[raw_u_tok]);
        let isCall = (raw_isCall == 'call') ? 1 : 0;
        let strike = params[3];
        let maturity = moment.utc(raw_maturity, 'YYYY-MM-DD HH:mm:ss').format('X');
        let now_time = moment.utc().format('YYYY-MM-DD HH:mm:ss').toString();
        let sell_orders;
        let buy_orders;
        try {
            let opt = new Option(eopt, f_tok, u_tok, isCall, strike, maturity);
            await opt.Init();
            sell_orders = await opt.GetOrders(1);
            buy_orders = await opt.GetOrders(0);
            if (opt.id == 0){
                console.log(`Error: no ord with params ${params.toString()}`);
                fs.appendFile(f_log, `Error: no opt with params ${params.toString()}`, ()=>{});
                continue;
            }
            let sell_orders_count = 0;
            for (let i = 0; i < sell_orders.owners.length; i++) {
                if ((sell_orders.owners[i] == conf.account.adr) && (sell_orders.amounts[i] > 0)) {
                    let ord_id = i;
                    let delta = parseFloat(sell_orders.deltas[i] / 10 ** 18);
                    let ref_price = parseFloat(sell_orders.ref_prices[i] / 10 ** 18).toFixed(2);
                    let price = (parseFloat((sell_orders.ord_prices[i] / 10 ** 18).toFixed(2)));
                    let type = 'sell';
                    let amount = (sell_orders.amounts[i] / 10 ** 18);
                    let toWrite = `${now_time},${ord_id},${raw_f_tok},${raw_u_tok},${raw_isCall},${strike},${raw_maturity},${type},${price},${ref_price},${delta},${amount}\n`;
                    fs.appendFileSync(f_out, toWrite);
                    sell_orders_count++;
                }
            }
            if (sell_orders_count == 0){
                let ord_id = -1;
                let delta = 0;
                let ref_price = 0;
                let price = 0;
                let type = 'sell';
                let amount = 0;
                let toWrite = `${now_time},${ord_id},${raw_f_tok},${raw_u_tok},${raw_isCall},${strike},${raw_maturity},${type},${price},${ref_price},${delta},${amount}\n`;
                fs.appendFileSync(f_out, toWrite);
            }
            let buy_orders_count = 0;
            for (let i = 0; i < buy_orders.owners.length; ++i) {
                if ((buy_orders.owners[i] == conf.account.adr) && (buy_orders.amounts[i] > 0)) {
                    let ord_id = i;
                    let delta = parseFloat(buy_orders.deltas[i] / 10 ** 18);
                    let ref_price = parseFloat(buy_orders.ref_prices[i] / 10 ** 18).toFixed(2);
                    let price = (parseFloat((buy_orders.ord_prices[i] / 10 ** 18).toFixed(2)));
                    let type = 'buy';
                    let amount = (buy_orders.amounts[i] / 10 ** 18);
                    let toWrite = `${now_time},${ord_id},${raw_f_tok},${raw_u_tok},${raw_isCall},${strike},${raw_maturity},${type},${price},${ref_price},${delta},${amount}\n`;
                   fs.appendFileSync(f_out, toWrite);
                    buy_orders_count++;
                }
            }
            if (buy_orders_count == 0){
                let ord_id = -1;
                let delta = 0;
                let ref_price = 0;
                let price = 0;
                let type = 'buy';
                let amount = 0;
                let toWrite = `${now_time},${ord_id},${raw_f_tok},${raw_u_tok},${raw_isCall},${strike},${raw_maturity},${type},${price},${ref_price},${delta},${amount}\n`;
                fs.appendFileSync(f_out, toWrite);
            }
        } catch (err) {
            fs.appendFile(f_log, `${now_time}: Option ${params} : ${err}\n`, () => {});
        }
    }
}
main();