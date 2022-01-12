import BN from 'bn.js';
import { dirname } from 'path';
import fs from 'fs';
import path from "path";
import { fileURLToPath } from 'url';
import Web3 from 'web3';
import fetch from 'node-fetch';

const __dirname = dirname(fileURLToPath(import.meta.url));
const conf = JSON.parse(fs.readFileSync(path.resolve(__dirname, '../config/config.cfg')).toString());
const web3 = new Web3(conf.net.httpProvider);

export async function getSign(f_tok, u_tok, date) {
    let data = JSON.stringify({
        "f_tok": f_tok,
        "u_tok": u_tok,
        "time": date,
    });

    let sign = await fetch(conf.net.url, {
        method: 'POST',
        body: data,
        headers: {
            'Content-Type': 'application/json'
        }
    });
    return await sign.json();
}

export async function sendTransaction(from, to, tr_data, gas_limit = 1000000) {

    let raw_tr = {
        "from": from.adr,
        "to": to,
        "gas": gas_limit,
        "chainId": conf.net.httpProviderChainId,
        "value": '0x00',
        "data": tr_data
    };

    let sign_tr = await web3.eth.accounts.signTransaction(raw_tr, from.pkey);
    let receipt = await web3.eth.sendSignedTransaction(sign_tr.rawTransaction);
    return receipt;
}

// export function signPrice(data) {

//     if (!web3.utils.isAddress(data.f_tok)) throw "f_tok address isn't valid";
//     if (!web3.utils.isAddress(data.u_tok)) throw "u_tok address isn't valid";

//     data.price = valToEth(data.price);
//     let form_data = web3.eth.abi.encodeParameters(
//         ['address', 'address', 'uint256', 'uint256'],
//         [data.f_tok, data.u_tok, data.price, data.time]
//     );
//     let sign_data = web3.eth.accounts.sign(form_data, conf.signer.pkey);

//     return { cur_price: data.price.toString(), v: sign_data.v, r: sign_data.r, s: sign_data.s };
// }

export function valToEth(val, dec = 18) {
    let arr = val.toString().split('.');

    if (arr.length == 1) return (new BN(arr[0] + '0'.repeat(dec)));

    return new BN(arr[0] + arr[1].slice(0, dec).padEnd(dec, '0'));
}

function EthToVal(val) {
    val = val.toString();
    return parseFloat(val.slice(0, val.length - 18) + '.' + val.slice(val.length - 18));
}

export class Option {
    constructor(eopt, f_token, u_token, type, strike_price, maturity_time) {
        this.eopt = eopt;
        this.f_token = f_token;
        this.u_token = u_token;
        this.type = type;
        this.strike_price = strike_price;
        this.maturity_time = maturity_time;
        this.id = 0;
    }

    // Отправляет запрос в БЧ, возвращает количество созданных опционов у переданного котракта
    static async GetOptCount(eopt) {
        return parseInt(await eopt.methods.GetOptCount().call());
    }

    // Возвращает информацию по опциону с переданным id в переданном контракте
    static async GetOpt(eopt, opt_id) {
        return await eopt.methods.GetOpt(opt_id).call();
    }

    static async GetCreatedOptCount(eopt, owner, opt_id) {
        return await eopt.methods.GetCreatedOptCount(owner.adr, opt_id).call();
    }

    // Выводит информацию, которая хранится в классе опциона
    async GetOptInfo() {
        let info = {
            eopt_adr: this.eopt._address,
            f_token: this.f_token._address,
            u_token: this.u_token._address,
            type: this.type,
            id: this.id,
            strike_price: this.strike_price.toString(),
            maturity_time: this.maturity_time,
            u_dec: this.u_dec.toString(),
        };
        return info;
    }

    // Возвращает количество созданных опционов данным пользователем
    async GetCreatedOpt(owner) {
        return await this.eopt.methods.GetCreatedOptCount(owner.adr, this.id).call();
    }

    // Возвращает информацию по ордерам указанного типа
    async GetOrders(type) {
        let orders = await this.eopt.methods.GetOrders(this.id, type).call();
        return {
            owners: orders.owners,
            amounts: orders.amounts,
            ref_prices: orders.ref_prices,
            deltas: orders.deltas,
            ord_prices: orders.ord_prices,
            max_ord_prices: orders.max_ord_prices,
            timestamp: orders.timestamp,
        };
    }

    static async GetTime(eopt) {
        return parseInt(await eopt.methods.now_time().call());
    }

    static async GetOptId(eopt, f_tok, u_tok, type, strike_price, maturity_time) {
        return parseInt(await eopt.methods.GetOptId(
            f_tok._address,
            u_tok._address,
            type,
            valToEth(strike_price),
            maturity_time
        ).call());
    }

    async Init() {
        this.id = await Option.GetOptId(
            this.eopt,
            this.f_token,
            this.u_token,
            this.type,
            this.strike_price,
            this.maturity_time
        );
    }


    async GetOptBalance(owner) {
        let balance = await this.eopt.methods.GetOptBalance(owner.adr, this.id).call();
        return {
            all: balance[0],
            locked: balance[1],
            exercised: balance[2]
        };
    }

    async CreateOpt(owner, amount) {
        amount = valToEth(amount);
        let data = this.eopt.methods.CreateOpt(
            this.f_token._address,
            this.u_token._address,
            this.type,
            valToEth(this.strike_price),
            this.maturity_time,
            amount
        ).encodeABI();
        let receipt = await sendTransaction(owner, this.eopt._address, data);
        if (this.id == 0) {
            this.id = await Option.GetOptId(this.eopt, this.f_token, this.u_token, this.type, this.strike_price, this.maturity_time);
        }

        return receipt;
    }

    async SetMaker(owner, address, isMaker) {
        let data = this.eopt.methods.SetMaker(address, isMaker).encodeABI();
        let receipt = await sendTransaction(owner, this.eopt._address, data);
        return receipt;
    }

    async CreateSellOrd(seller, amount, ref_price, delta, ord_price, min_price) {
        ref_price = valToEth(ref_price);
        delta = valToEth(delta);
        ord_price = valToEth(ord_price);
        amount = valToEth(amount);
        min_price = valToEth(min_price);
        let data = this.eopt.methods.MakeSellOrd(this.id, amount, ref_price, delta, ord_price, min_price).encodeABI();
        return await sendTransaction(seller, this.eopt._address, data);
    }

    async TakeBuyOrd(buyer, ord_id, amount, cur_price, time, v, r, s) {
        amount = valToEth(amount);
        let data = this.eopt.methods.TakeBuyOrd(this.id, ord_id, amount, cur_price, time, v, r, s).encodeABI();
        return await sendTransaction(buyer, this.eopt._address, data);

    }

    async ChangeSellOrd(seller, ord_id, amount, ref_price, delta, ord_price, min_price) {
        ref_price = valToEth(ref_price);
        delta = valToEth(delta);
        ord_price = valToEth(ord_price);
        amount = valToEth(amount);
        min_price = valToEth(min_price);
        let data = this.eopt.methods.ChangeSellOrd(this.id, ord_id, amount, ref_price, delta, ord_price, min_price).encodeABI();
        return await sendTransaction(seller, this.eopt._address, data);
    }

    async CreateBuyOrd(buyer, amount, ref_price, delta, ord_price, max_price) {
        ref_price = valToEth(ref_price);
        delta = valToEth(delta);
        ord_price = valToEth(ord_price);
        amount = valToEth(amount);
        max_price = valToEth(max_price);
        let data = this.eopt.methods.MakeBuyOrd(this.id, amount, ref_price, delta, ord_price, max_price).encodeABI();
        return await sendTransaction(buyer, this.eopt._address, data);
    }

    async TakeSellOrd(seller, ord_id, amount, cur_price, time, v, r, s) {
        amount = valToEth(amount);
        let data = this.eopt.methods.TakeSellOrd(this.id, ord_id, amount, cur_price, time, v, r, s).encodeABI();
        return await sendTransaction(seller, this.eopt._address, data);

    }

    async ChangeBuyOrd(seller, ord_id, amount, ref_price, delta, ord_price, max_price) {
        ref_price = valToEth(ref_price);
        delta = valToEth(delta);
        ord_price = valToEth(ord_price);
        amount = valToEth(amount);
        max_price = valToEth(max_price);
        let data = this.eopt.methods.ChangeBuyOrd(this.id, ord_id, amount, ref_price, delta, ord_price, max_price).encodeABI();
        return await sendTransaction(seller, this.eopt._address, data);
    }

    async MatchOrds(matcher, sell_ord_id, buy_ord_id, cur_price, time, v, r, s) {
        let data = this.eopt.methods.MatchOrds(this.id, sell_ord_id, buy_ord_id, cur_price, time, v, r, s).encodeABI();
        return await sendTransaction(matcher, this.eopt._address, data);
    }

    async RequestOptExercise(exerciser, amount) {
        amount = valToEth(amount);
        let data = this.eopt.methods.RequestOptExercise(this.id, amount).encodeABI();
        return await sendTransaction(exerciser, this.eopt._address, data);
    }

    async FinalizeOptExercise(exerciser) {
        let data = this.eopt.methods.FinalizeOptExercise(exerciser.adr, this.id).encodeABI();
        return await sendTransaction(exerciser, this.eopt._address, data);
    }

    async WithdrawOpt(owner) {
        let data = this.eopt.methods.WithdrawOpt(owner.adr, this.id).encodeABI();
        return await sendTransaction(owner, this.eopt._address, data);
    }

}

export { web3 };
